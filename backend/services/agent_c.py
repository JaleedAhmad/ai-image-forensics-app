import os
import json
import logging
import asyncio
from openai import AsyncOpenAI
from groq import AsyncGroq
from models.agent_schema import AgentReport, FinalVerdict, AgentFinding

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Agent C — the Forensic Arbitrator. You do not see images.
You receive two specialist reports and issue the final binding verdict.

Your responsibilities:
1. Identify where Agent A and Agent B agree — this is your strongest evidence
2. Identify where they conflict — explain which argument is stronger and why
3. Weight findings by severity — critical findings from either agent carry more weight
4. Issue a final verdict with a calibrated confidence score

Confidence calibration rules:
- Both agents agree with high severity findings -> confidence 0.85-1.0
- Both agents agree with medium findings -> confidence 0.65-0.84
- Agents partially agree -> confidence 0.45-0.64
- Agents conflict -> confidence 0.25-0.44
- Insufficient evidence from both -> confidence 0.0-0.24, verdict: uncertain

You return ONLY a JSON object matching the FinalVerdict schema. No preamble. No markdown. Raw JSON only."""


async def _call_cerebras(
    client: AsyncOpenAI, model_name: str, messages: list
) -> tuple[str, str]:
    logger.info(f"Calling Cerebras model: {model_name}")
    response = await client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    actual_model = getattr(response, "model", model_name)
    return response.choices[0].message.content, actual_model


async def _call_groq_fallback(messages: list) -> FinalVerdict:
    logger.info("Falling back Arbitrator to Groq...")
    client = AsyncGroq()
    model_name = "llama-3.3-70b-versatile"
    response = await client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    verdict = FinalVerdict.model_validate_json(response.choices[0].message.content)
    verdict.providers_used.append(response.model)
    verdict.degraded_mode = True
    return verdict


async def run_agent_c(report_a: AgentReport, report_b: AgentReport) -> FinalVerdict:
    model_name = "zai-glm-4.7"
    client = AsyncOpenAI(
        base_url="https://api.cerebras.ai/v1",
        api_key=os.environ.get("CEREBRAS_API_KEY"),
    )

    report_a_json = report_a.model_dump_json(indent=2)
    report_b_json = report_b.model_dump_json(indent=2)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Agent A Report:\n{report_a_json}\n\nAgent B Report:\n{report_b_json}\n\nPlease provide your final verdict as a JSON object matching the FinalVerdict schema:\n{json.dumps(FinalVerdict.model_json_schema(), indent=2)}",
        },
    ]

    async def _attempt_parse() -> FinalVerdict:
        text_response, actual_model = await _call_cerebras(client, model_name, messages)
        try:
            verdict = FinalVerdict.model_validate_json(text_response)
            verdict.providers_used = [actual_model]
            return verdict
        except Exception as e:
            logger.warning(
                f"Failed to parse initial JSON response from Cerebras: {e}. Retrying."
            )
            retry_messages = messages + [
                {"role": "assistant", "content": text_response},
                {
                    "role": "user",
                    "content": "The previous response was invalid JSON or did not match the schema. Please return ONLY a valid JSON object matching the FinalVerdict schema without any Markdown formatting or preamble.",
                },
            ]
            retry_text_response, actual_model_retry = await _call_cerebras(
                client, model_name, retry_messages
            )
            verdict = FinalVerdict.model_validate_json(retry_text_response)
            verdict.providers_used = [actual_model_retry]
            return verdict

    try:
        verdict = await asyncio.wait_for(_attempt_parse(), timeout=40.0)
        verdict.degraded_mode = False
        return verdict
    except Exception as e:
        logger.error(f"Agent C Cerebras primary failed: {e}")
        try:
            return await asyncio.wait_for(_call_groq_fallback(messages), timeout=30.0)
        except Exception as fallback_e:
            logger.error(f"Agent C Groq fallback also failed: {fallback_e}")
            finding = AgentFinding(
                type="arbitration_failure",
                severity="critical",
                description=f"Arbitrator experienced a total failure: {str(e)} | Fallback: {str(fallback_e)}",
                location=None,
            )
            return FinalVerdict(
                thinking="Fallback due to failure. No reasoning available.",
                verdict="uncertain",
                confidence=0.0,
                consensus="conflict",
                agent_a_report=report_a,
                agent_b_report=report_b,
                arbitrator_reasoning=f"Arbitrator experienced a total failure during evaluation: {str(e)}",
                key_evidence=["Arbitration failure"],
                artifact_locations=[finding],
                providers_used=[model_name],
                degraded_mode=True,
            )
