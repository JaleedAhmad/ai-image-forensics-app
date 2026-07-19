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
- low: minor inconsistency, noted for completeness"""


async def run_agent_a(
    original_image_bytes: bytes, ela_image_bytes: bytes, metadata: dict, scene_profile: SceneProfile
) -> AgentReport:
    model_name = "gemini-2.5-flash"
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"), http_options={"api_version": "v1beta"}
    )

    parts = [
        types.Part.from_bytes(data=original_image_bytes, mime_type="image/jpeg"),
        types.Part.from_bytes(data=ela_image_bytes, mime_type="image/jpeg"),
        f"Scene Context Profile (from Agent 0):\n{scene_profile.model_dump_json(indent=2)}\n\nOriginal Image Metadata:\n{json.dumps(metadata, indent=2)}\n\nPlease provide your analysis.",
    ]

    try:

        async def call():
            return await client.aio.models.generate_content(
                model=model_name,
                contents=parts,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=AgentReport,
                    temperature=0.0,
                ),
            )

        async def _attempt() -> AgentReport:
            response = await asyncio.wait_for(call(), timeout=60.0)
            report = AgentReport.model_validate_json(response.text)
            report.provider = model_name
            report.agent = "metadata_analyst"
            return report

        try:
            return await _attempt()
        except Exception as e:
            logger.warning(
                f"Agent A analysis failed on first attempt: {e}. Retrying."
            )
            await asyncio.sleep(2)
            return await _attempt()

    except Exception as e:
        import traceback
        full_traceback = traceback.format_exc()
        logger.error(f"Agent A encountered a total failure: {e}\nTraceback:\n{full_traceback}")
        
        error_msg = str(e) or f"{type(e).__name__} (no message)"
        finding = AgentFinding(
            type="agent_failure",
            severity="critical",
            description=f"Agent A failed to generate a valid report: {error_msg}",
            location=None,
        )
        return AgentReport(
            thinking="Fallback due to failure. No reasoning available.",
            agent="metadata_analyst",
            provider=model_name,
            findings=[finding],
            manipulation_indicators=0,
            authenticity_indicators=0,
            confidence=0.0,
            preliminary_verdict="uncertain",
            reasoning_summary="Agent experienced a total failure during analysis or JSON parsing.",
        )
