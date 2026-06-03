import json
import base64
import logging
import asyncio
from groq import AsyncGroq
from models.agent_schema import AgentReport, AgentFinding

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
    response = await client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.0,
    )

    # Log actual model ID that responded
    actual_model = response.model
    logger.info(f"Groq model that actually responded: {actual_model}")

    return response.choices[0].message.content, actual_model


async def run_agent_b(
    original_image_bytes: bytes, edge_map_bytes: bytes
) -> AgentReport:
    model_name = "meta-llama/llama-4-scout-17b-16e-instruct"

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
                    "text": f"Analyze these images (original and edge map) and return your report strictly as a JSON object matching this schema:\n{json.dumps(AgentReport.model_json_schema(), indent=2)}",
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

    async def _attempt_parse() -> AgentReport:
        # First attempt
        text_response, actual_model = await _call_groq(client, model_name, messages)
        try:
            report = AgentReport.model_validate_json(text_response)
            report.provider = actual_model
            return report
        except Exception as e:
            logger.warning(
                f"Failed to parse initial JSON response from Groq: {e}. Retrying with simpler prompt."
            )

            # Retry attempt
            retry_messages = messages + [
                {"role": "assistant", "content": text_response},
                {
                    "role": "user",
                    "content": f"The previous response was invalid JSON or did not match the schema. Please return ONLY a valid JSON object matching this exact schema:\n{json.dumps(AgentReport.model_json_schema(), indent=2)}\nWithout any Markdown formatting or preamble.",
                },
            ]

            retry_text_response, actual_model_retry = await _call_groq(
                client, model_name, retry_messages
            )
            report = AgentReport.model_validate_json(retry_text_response)
            report.provider = actual_model_retry
            return report

    try:
        # Timeout after 25 seconds (Groq is faster, shorter timeout is fine)
        report = await asyncio.wait_for(_attempt_parse(), timeout=25.0)

        # Ensure the agent type is correctly assigned
        report.agent = "semantic_auditor"
        return report

    except Exception as e:
        logger.error(f"Agent B encountered a total failure: {e}")
        # On total failure return a degraded AgentReport with confidence: 0.0
        finding = AgentFinding(
            type="agent_failure",
            severity="critical",
            description=f"Agent B failed to generate a valid report: {str(e)}",
            location=None,
        )
        return AgentReport(
            thinking="Fallback due to failure. No reasoning available.",
            agent="semantic_auditor",
            provider=model_name,
            findings=[finding],
            manipulation_indicators=0,
            authenticity_indicators=0,
            confidence=0.0,
            preliminary_verdict="uncertain",
            reasoning_summary="Agent experienced a total failure during semantic analysis or JSON parsing.",
        )
