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


async def _call_groq(
    client: AsyncGroq, model_name: str, messages: list
) -> tuple[str, str]:
    logger.info(f"Calling Groq model: {model_name}")
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=4000,
            temperature=0.0,
        )
    except Exception as e:
        import groq
        if isinstance(e, groq.APIStatusError) and hasattr(e, 'response'):
            logger.error(f"Groq API Error in _call_groq: {e}. RAW RESPONSE: {e.response.text}")
        raise e

    # Log actual model ID that responded
    actual_model = response.model
    logger.info(f"Groq model that actually responded: {actual_model}")

    return response.choices[0].message.content, actual_model


async def run_agent_b(
    original_image_bytes: bytes, edge_map_bytes: bytes, scene_profile: SceneProfile
) -> AgentReport:
    # Note: qwen/qwen3.6-27b is currently Groq's only vision-capable model and is
    # preview status (not production-guaranteed, may be discontinued without notice).
    # This is a deliberate, accepted tradeoff, documented so it's not mistaken for an oversight later.
    model_name = "qwen/qwen3.6-27b"

    # Initialize the Groq client. Relies on GROQ_API_KEY environment variable.
    client = AsyncGroq()

    # Base64 encode the images for the standard OpenAI-compatible image_url format
    original_b64 = base64.b64encode(original_image_bytes).decode("utf-8")
    edge_map_b64 = base64.b64encode(edge_map_bytes).decode("utf-8")

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
