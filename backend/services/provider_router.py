import time
import os
import asyncio
import logging
from typing import Tuple
import json
import base64

from groq import AsyncGroq
from google import genai
from google.genai import types

from models.agent_schema import AgentReport, AgentFinding
from services.agent_a import run_agent_a, SYSTEM_PROMPT as AGENT_A_PROMPT
from services.agent_b import run_agent_b, SYSTEM_PROMPT as AGENT_B_PROMPT

logger = logging.getLogger(__name__)

PROVIDER_STATUS = {
    "gemini": {"status": False, "last_checked": 0},
    "groq": {"status": False, "last_checked": 0},
    "cerebras": {"status": False, "last_checked": 0},
}
CACHE_TTL = 300


async def check_provider_health(provider: str) -> bool:
    now = time.time()
    cache = PROVIDER_STATUS.get(provider)
    if cache and (now - cache["last_checked"] < CACHE_TTL):
        return cache["status"]

    status = False
    try:
        if provider == "gemini":
            client = genai.Client(
                api_key=os.environ.get("GEMINI_API_KEY"),
                http_options={"api_version": "v1beta"},
            )
            await client.aio.models.generate_content(
                model="gemini-2.0-flash", contents="ping"
            )
            status = True
        elif provider == "groq":
            client = AsyncGroq()
            await client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=2,
            )
            status = True
        elif provider == "cerebras":
            # pyrefly: ignore [missing-import]
            from openai import AsyncOpenAI

            c_client = AsyncOpenAI(
                base_url="https://api.cerebras.ai/v1",
                api_key=os.environ.get("CEREBRAS_API_KEY"),
            )
            await c_client.chat.completions.create(
                model="zai-glm-4.7",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=2,
            )
            status = True
    except Exception as e:
        logger.error(f"Health check failed for {provider}: {e}")
        status = False

    PROVIDER_STATUS[provider] = {"status": status, "last_checked": now}
    return status


async def _fallback_agent_a_on_groq(
    original_bytes: bytes, ela_bytes: bytes, metadata: dict
) -> AgentReport:
    model_name = "meta-llama/llama-4-scout-17b-16e-instruct"
    client = AsyncGroq()
    original_b64 = base64.b64encode(original_bytes).decode("utf-8")
    ela_b64 = base64.b64encode(ela_bytes).decode("utf-8")

    messages = [
        {"role": "system", "content": AGENT_A_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Original Image Metadata:\n{json.dumps(metadata, indent=2)}\n\nPlease provide your analysis strictly as a JSON object matching this schema:\n{json.dumps(AgentReport.model_json_schema(), indent=2)}",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{original_b64}"},
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{ela_b64}"},
                },
            ],
        },
    ]

    try:

        async def call():
            return await client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,
            )

        resp = await asyncio.wait_for(call(), timeout=25.0)
        report = AgentReport.model_validate_json(resp.choices[0].message.content)
        report.provider = resp.model
        report.agent = "metadata_analyst"
        return report
    except Exception as e:
        logger.error(f"Fallback Agent A on Groq failed: {e}")
        finding = AgentFinding(
            type="agent_failure",
            severity="critical",
            description=f"Fallback failed: {e}",
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
            reasoning_summary="Fallback failure on Groq.",
        )


async def _fallback_agent_b_on_gemini(
    original_bytes: bytes, edge_bytes: bytes
) -> AgentReport:
    model_name = "gemini-2.0-flash"
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"), http_options={"api_version": "v1beta"}
    )

    parts = [
        types.Part.from_bytes(data=original_bytes, mime_type="image/jpeg"),
        types.Part.from_bytes(data=edge_bytes, mime_type="image/jpeg"),
        "Analyze these images (original and edge map) and return your report.",
    ]

    try:

        async def call():
            return await client.aio.models.generate_content(
                model=model_name,
                contents=parts,
                config=types.GenerateContentConfig(
                    system_instruction=AGENT_B_PROMPT,
                    response_mime_type="application/json",
                    response_schema=AgentReport,
                    temperature=0.0,
                ),
            )

        resp = await asyncio.wait_for(call(), timeout=30.0)
        report = AgentReport.model_validate_json(resp.text)
        report.provider = model_name
        report.agent = "semantic_auditor"
        return report
    except Exception as e:
        logger.error(f"Fallback Agent B on Gemini failed: {e}")
        finding = AgentFinding(
            type="agent_failure",
            severity="critical",
            description=f"Fallback failed: {e}",
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
            reasoning_summary="Fallback failure on Gemini.",
        )


async def run_vision_agents(
    original_bytes: bytes, ela_bytes: bytes, edge_bytes: bytes, metadata: dict
) -> Tuple[AgentReport, AgentReport]:
    gemini_health = await check_provider_health("gemini")
    groq_health = await check_provider_health("groq")

    task_a = (
        run_agent_a(original_bytes, ela_bytes, metadata)
        if gemini_health
        else _fallback_agent_a_on_groq(original_bytes, ela_bytes, metadata)
    )
    task_b = (
        run_agent_b(original_bytes, edge_bytes)
        if groq_health
        else _fallback_agent_b_on_gemini(original_bytes, edge_bytes)
    )

    res_a, res_b = await asyncio.gather(task_a, task_b, return_exceptions=True)

    if isinstance(res_a, Exception):
        logger.error(f"Agent A primary failed: {res_a}")
        res_a = await _fallback_agent_a_on_groq(original_bytes, ela_bytes, metadata)
        res_a.degraded_mode = True

    if isinstance(res_b, Exception):
        logger.error(f"Agent B primary failed: {res_b}")
        res_b = await _fallback_agent_b_on_gemini(original_bytes, edge_bytes)
        res_b.degraded_mode = True

    return res_a, res_b
