import os
import json
import logging
import asyncio
from typing import Dict, Any
from google import genai
from google.genai import types
from models.agent_schema import AgentReport, AgentFinding, SceneProfile

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Agent A — a cold, precise Metadata and Compression Forensics Specialist.
Your jurisdiction is strictly limited to:
1. ELA (Error Level Analysis) heatmap anomalies — brightness spikes indicating re-compression
2. File signature analysis — EXIF metadata, software tags, AI generator signatures
3. Compression artifact inconsistencies — mismatched quality levels across regions

You do NOT comment on content, semantics, or visual plausibility. That is another agent's job.
You return ONLY a JSON object matching the AgentReport schema. No preamble. No explanation outside the JSON.

Severity guide:
- critical: definitive manipulation signature (known AI generator tag, impossible ELA pattern)
- high: strong anomaly with no innocent explanation
- medium: suspicious pattern that could have innocent cause
- low: minor inconsistency, noted for completeness
- none: positive evidence of authenticity (e.g., "original camera EXIF tags intact"). If the image is authentic, you MUST still log your positive evidence in the findings array using severity="none"."""


async def run_agent_a(
    original_image_bytes: bytes, ela_image_bytes: bytes, metadata: dict, scene_profile: SceneProfile
) -> AgentReport:
    model_name = "gemini-2.0-flash"
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"), http_options={"api_version": "v1beta"}
    )

    parts = [
        types.Part.from_bytes(data=original_image_bytes, mime_type="image/jpeg"),
        types.Part.from_bytes(data=ela_image_bytes, mime_type="image/jpeg"),
        f"Scene Context Profile (from Agent 0):\n{scene_profile.model_dump_json(indent=2)}\n\nOriginal Image Metadata:\n{json.dumps(metadata, indent=2)}\n\nPlease provide your analysis.",
    ]

    from services.llm_utils import call_llm_with_json_validation
    
    return await call_llm_with_json_validation(
        provider="gemini",
        client=client,
        model_name=model_name,
        system_prompt=SYSTEM_PROMPT,
        payload=parts,
        schema=AgentReport,
        agent_name="metadata_analyst",
        timeout=60.0,
        max_tokens=4000,
        max_retries=1,
    )
