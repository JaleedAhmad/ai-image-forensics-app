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

from models.agent_schema import AgentReport, AgentFinding, SceneProfile
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
                model="qwen/qwen3.6-27b",
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
    original_bytes: bytes, ela_bytes: bytes, metadata: dict, scene_profile: SceneProfile
) -> AgentReport:
    model_name = "qwen/qwen3.6-27b"
    client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))

    from PIL import Image
    import io
    
    TEXT_BASELINE_TOKENS = 1263
    
    # Dynamically estimate metadata and scene profile variation size (~4 chars per token)
    dynamic_text_tokens = (len(json.dumps(metadata)) + len(scene_profile.model_dump_json())) / 4
    total_text_overhead = TEXT_BASELINE_TOKENS + dynamic_text_tokens

    # Check token budget for Groq (8000 TPM limit, max_tokens=4000, leaving ~4000 for visual + text payload)
    # Qwen-VL empirical limit is a flat ~1800 tokens per image. Since we only send the ELA map now, it's just 1800.
    estimated_image_tokens = 1800
    total_estimated_tokens = estimated_image_tokens + total_text_overhead
    
    if total_estimated_tokens > 3900:
        logger.warning(f"Aborting Agent A fallback: Estimated total tokens ({total_estimated_tokens:.0f}) exceed 3900 budget (Image: {estimated_image_tokens:.0f}, Text: {total_text_overhead}).")
        finding = AgentFinding(
            type="agent_failure",
            severity="critical",
            description=f"Image too large for Groq fallback (Estimated total tokens: {total_estimated_tokens:.0f}) — Gemini primary required.",
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
            reasoning_summary="Fallback aborted due to image size limitations.",
        )

    ela_b64 = base64.b64encode(ela_bytes).decode("utf-8")

    messages = [
        {"role": "system", "content": AGENT_A_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Original Image Metadata:\n{json.dumps(metadata, indent=2)}\n\nScene Context Profile (from Agent 0):\n{scene_profile.model_dump_json(indent=2)}\n\nPlease provide your analysis of this ELA map strictly as a JSON object matching this schema:\n{json.dumps(AgentReport.model_json_schema(), indent=2)}",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{ela_b64}"},
                },
            ],
        },
    ]

    from services.llm_utils import call_llm_with_json_validation
    
    return await call_llm_with_json_validation(
        provider="groq",
        client=client,
        model_name=model_name,
        system_prompt=AGENT_A_PROMPT,
        payload=messages,
        schema=AgentReport,
        agent_name="metadata_analyst",
        timeout=60.0,
        max_tokens=4000,
        max_retries=1,
    )


async def _fallback_agent_b_on_gemini(
    original_bytes: bytes, edge_bytes: bytes, scene_profile: SceneProfile
) -> AgentReport:
    model_name = "gemini-2.0-flash"
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"), http_options={"api_version": "v1beta"}
    )

    parts = [
        types.Part.from_bytes(data=original_bytes, mime_type="image/jpeg"),
        types.Part.from_bytes(data=edge_bytes, mime_type="image/jpeg"),
        f"Scene Context Profile (from Agent 0):\n{scene_profile.model_dump_json(indent=2)}\n\nAnalyze these images (original and edge map) and return your report.",
    ]

    from services.llm_utils import call_llm_with_json_validation
    
    return await call_llm_with_json_validation(
        provider="gemini",
        client=client,
        model_name=model_name,
        system_prompt=AGENT_B_PROMPT,
        payload=parts,
        schema=AgentReport,
        agent_name="semantic_auditor",
        timeout=60.0,
        max_tokens=4000,
        max_retries=1,
    )


async def run_vision_agents(
    original_bytes: bytes, ela_bytes: bytes, edge_bytes: bytes, metadata: dict, scene_profile: SceneProfile
) -> Tuple[AgentReport, AgentReport]:
    gemini_health = await check_provider_health("gemini")
    groq_health = await check_provider_health("groq")

    task_a = (
        run_agent_a(original_bytes, ela_bytes, metadata, scene_profile)
        if gemini_health
        else _fallback_agent_a_on_groq(original_bytes, ela_bytes, metadata, scene_profile)
    )
    task_b = (
        run_agent_b(original_bytes, edge_bytes, scene_profile)
        if groq_health
        else _fallback_agent_b_on_gemini(original_bytes, edge_bytes, scene_profile)
    )

    res_a, res_b = await asyncio.gather(task_a, task_b, return_exceptions=True)

    if isinstance(res_a, Exception):
        logger.error(f"Agent A primary failed: {res_a}")
        res_a = await _fallback_agent_a_on_groq(original_bytes, ela_bytes, metadata, scene_profile)
        res_a.degraded_mode = True

    if isinstance(res_b, Exception):
        logger.error(f"Agent B primary failed: {res_b}")
        res_b = await _fallback_agent_b_on_gemini(original_bytes, edge_bytes, scene_profile)
        res_b.degraded_mode = True

    return res_a, res_b
