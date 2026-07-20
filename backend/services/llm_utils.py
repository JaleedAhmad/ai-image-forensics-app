import json
import logging
import asyncio
from typing import Type, Any, Literal, Optional, List
from pydantic import BaseModel
from google.genai import types

from models.agent_schema import AgentReport, AgentFinding

logger = logging.getLogger(__name__)

async def _call_groq(client, model_name: str, messages: list, max_tokens: int, timeout: float) -> tuple[str, str]:
    async def call():
        return await client.chat.completions.create(
            model=model_name,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
            temperature=0.0,
        )
    resp = await asyncio.wait_for(call(), timeout=timeout)
    return resp.choices[0].message.content, resp.model

async def _call_gemini(client, model_name: str, system_prompt: str, contents: list, schema: Type[BaseModel], max_tokens: int, timeout: float) -> tuple[str, str]:
    async def call():
        return await client.aio.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.0,
                max_output_tokens=max_tokens,
            ),
        )
    resp = await asyncio.wait_for(call(), timeout=timeout)
    return resp.text, model_name

async def call_llm_with_json_validation(
    provider: Literal["groq", "gemini"],
    client: Any,
    model_name: str,
    system_prompt: str,
    payload: list,
    schema: Type[BaseModel],
    agent_name: str,
    timeout: float = 60.0,
    max_tokens: int = 4000,
    max_retries: int = 1,
) -> BaseModel:
    """
    Shared helper to call an LLM (Groq or Gemini) and validate against a Pydantic schema.
    Handles per-attempt timeouts, explicit max_tokens, validation loops, and safe fallback.
    """
    attempts = 0
    current_payload = list(payload)
    
    # Store the last exception to use in the fallback report
    last_exception = None
    
    while attempts <= max_retries:
        try:
            if provider == "groq":
                text_response, actual_model = await _call_groq(client, model_name, current_payload, max_tokens, timeout)
            elif provider == "gemini":
                text_response, actual_model = await _call_gemini(client, model_name, system_prompt, current_payload, schema, max_tokens, timeout)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
                
            report = schema.model_validate_json(text_response)
            
            # Populate common tracking fields if present
            if hasattr(report, "provider"):
                report.provider = actual_model
            if hasattr(report, "agent"):
                report.agent = agent_name
                
            return report
            
        except Exception as e:
            last_exception = e
            logger.warning(f"[{agent_name}] Attempt {attempts + 1} failed: {e}")
            
            # If we haven't exhausted retries, inject the error into the prompt and retry
            if attempts < max_retries:
                # We need to construct the retry prompt depending on the provider format
                # We don't always have text_response (e.g. if it was a TimeoutError), 
                # so we only append the assistant response if it exists.
                error_context = f"Your previous response failed validation with this error:\n{e}\n\nPlease return ONLY a valid JSON object exactly matching the schema. Do not include Markdown formatting or any other text."
                
                try:
                    _ = text_response
                except NameError:
                    text_response = "Error: no response generated."
                    
                if provider == "groq":
                    current_payload.append({"role": "assistant", "content": text_response})
                    current_payload.append({"role": "user", "content": error_context})
                elif provider == "gemini":
                    current_payload.append(types.Content(role="model", parts=[types.Part.from_text(text=text_response)]))
                    current_payload.append(types.Content(role="user", parts=[types.Part.from_text(text=error_context)]))
                    
            attempts += 1
            
    # Exhausted retries or fatal error: return a safe fallback object
    import traceback
    full_traceback = traceback.format_exc()
    logger.error(f"[{agent_name}] encountered a total failure: {last_exception}\nTraceback:\n{full_traceback}")
    
    error_msg = str(last_exception) or f"{type(last_exception).__name__} (no message)"
    
    if schema is AgentReport:
        finding = AgentFinding(
            type="agent_failure",
            severity="critical",
            description=f"{agent_name.replace('_', ' ').title()} failed to generate a valid report: {error_msg}",
            location=None,
        )
        return AgentReport(
            thinking="Fallback due to failure. No reasoning available.",
            agent=agent_name,
            provider=model_name,
            findings=[finding],
            manipulation_indicators=0,
            authenticity_indicators=0,
            confidence=0.0,
            preliminary_verdict="uncertain",
            reasoning_summary="Agent experienced a total failure during analysis or JSON parsing.",
        )
    else:
        # Generic fallback for other schemas if needed in the future
        raise RuntimeError(f"Total failure for {agent_name}: {error_msg}") from last_exception
