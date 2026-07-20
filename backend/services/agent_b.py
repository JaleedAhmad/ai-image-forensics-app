import json
import base64
import logging
import asyncio
from groq import AsyncGroq
from models.agent_schema import AgentReport, AgentFinding, SceneProfile

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Agent B — a sharp, adversarial Semantic and Geometric Plausibility Auditor.
Your jurisdiction is strictly limited to:
1. Lighting and shadow consistency — do light sources match across the scene?
2. Geometric integrity — perspective, proportions, edge continuity
3. Semantic plausibility — physically impossible elements, anatomical failures
4. Texture boundary analysis — unnatural transitions between regions using the edge map

You are adversarial by nature. Assume manipulation until the evidence proves otherwise.
You do NOT analyze compression, metadata, or file signatures. That is another agent's job.
You return ONLY a JSON object matching the AgentReport schema. No preamble. No explanation outside the JSON.

Severity guide:
- critical: physically impossible element (impossible shadow direction, broken perspective)
- high: strong geometric or semantic failure with no natural explanation
- medium: suspicious inconsistency that warrants flagging
- low: minor anomaly, could be natural"""

from PIL import Image
import io
import math

def _resize_for_token_budget(image_bytes: bytes, token_budget: int = 1500) -> bytes:
    # Qwen-VL empirical ratio from testing: ~0.00096 tokens per pixel
    tokens_per_pixel = 0.0009605
    max_pixels = token_budget / tokens_per_pixel
    
    with Image.open(io.BytesIO(image_bytes)) as img:
        # Convert to RGB if necessary before saving to JPEG
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        current_pixels = img.width * img.height
        if current_pixels <= max_pixels:
            return image_bytes
            
        scale_factor = math.sqrt(max_pixels / current_pixels)
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)
        
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        resized_img.save(out, format="JPEG", quality=95)
        return out.getvalue()





async def run_agent_b(
    original_image_bytes: bytes, edge_map_bytes: bytes, scene_profile: SceneProfile
) -> AgentReport:
    # Note: qwen/qwen3.6-27b is currently Groq's only vision-capable model and is
    # preview status (not production-guaranteed, may be discontinued without notice).
    # This is a deliberate, accepted tradeoff, documented so it's not mistaken for an oversight later.
    model_name = "qwen/qwen3.6-27b"

    # Initialize the Groq client. Relies on GROQ_API_KEY environment variable.
    client = AsyncGroq()

    # Apply dynamic resizing to fit the ~1500 token-per-image budget
    resized_original = _resize_for_token_budget(original_image_bytes)
    resized_edge = _resize_for_token_budget(edge_map_bytes)

    # Base64 encode the resized images for the standard OpenAI-compatible image_url format
    original_b64 = base64.b64encode(resized_original).decode("utf-8")
    edge_map_b64 = base64.b64encode(resized_edge).decode("utf-8")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Scene Context Profile (from Agent 0):\n{scene_profile.model_dump_json(indent=2)}\n\nAnalyze these images (original and edge map) and return your report strictly as a JSON object matching this schema:\n{json.dumps(AgentReport.model_json_schema(), indent=2)}",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{original_b64}"},
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{edge_map_b64}"},
                },
            ],
        },
    ]

    from services.llm_utils import call_llm_with_json_validation

    return await call_llm_with_json_validation(
        provider="groq",
        client=client,
        model_name=model_name,
        system_prompt=SYSTEM_PROMPT,
        payload=messages,
        schema=AgentReport,
        agent_name="semantic_auditor",
        timeout=60.0,
        max_tokens=4000,
        max_retries=1,
    )
