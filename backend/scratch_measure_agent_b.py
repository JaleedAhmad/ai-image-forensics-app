import asyncio
import os
import json
from dotenv import load_dotenv
from groq import AsyncGroq
from models.agent_schema import AgentReport, SceneProfile, VisibleText
from services.agent_b import SYSTEM_PROMPT

load_dotenv()

async def measure_agent_b_payload():
    client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
    
    scene_profile = SceneProfile(
        medium="photograph",
        medium_confidence="high",
        medium_reasoning="Looks like a photo.",
        subject_description="A cat.",
        human_subjects_present=False,
        human_subject_notes=None,
        lighting_and_physics_notes="Normal lighting.",
        stylistic_elements_that_mimic_flaws=[],
        visible_text=VisibleText(present=False, transcription="", text_context=""),
        setting="real_world_photographable",
        setting_notes=None,
        image_quality_notes="High resolution.",
        flags_for_downstream_agents=""
    )
    
    text_prompt = f"Scene Context Profile (from Agent 0):\n{scene_profile.model_dump_json(indent=2)}\n\nAnalyze these images (original and edge map) and return your report strictly as a JSON object matching this schema:\n{json.dumps(AgentReport.model_json_schema(), indent=2)}"
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text_prompt}
    ]
    
    resp = await client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=messages,
        max_tokens=10,
    )
    print(f"[Agent B] Text Baseline Tokens: {resp.usage.prompt_tokens}")

if __name__ == "__main__":
    asyncio.run(measure_agent_b_payload())
