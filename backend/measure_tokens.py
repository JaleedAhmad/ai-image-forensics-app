import asyncio
import os
import json
from dotenv import load_dotenv
load_dotenv()
from groq import AsyncGroq
from models.agent_schema import AgentReport, SceneProfile

async def main():
    client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
    model_name = "qwen/qwen3.6-27b"
    
    # We will simulate a very long/complex response by asking the model to list 10 geometric anomalies
    system_prompt = "You are a geometric plausibility auditor. You must identify exactly 10 distinct, highly detailed geometric anomalies in the provided scene context. Return a JSON matching the AgentReport schema."
    
    scene_profile = SceneProfile(
        medium="digital_painting",
        medium_confidence="high",
        medium_reasoning="Looks like a digital painting with impossible geometry.",
        subject_description="A complex architectural scene with M.C. Escher-like stairs.",
        human_subjects_present=False,
        human_subject_notes="",
        lighting_and_physics_notes="Multiple conflicting light sources.",
        stylistic_elements_that_mimic_flaws=["Impossible geometry", "Escher stairs"],
        visible_text={"present": False, "transcription": "", "text_context": ""},
        setting="fictional_or_impossible",
        setting_notes="Impossible stairs everywhere.",
        image_quality_notes="High resolution, complex details.",
        flags_for_downstream_agents="Flag geometric impossibility."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Scene Context Profile:\n{scene_profile.model_dump_json(indent=2)}\n\nPlease return ONLY a valid JSON object matching this exact schema:\n{json.dumps(AgentReport.model_json_schema(), indent=2)}"
        }
    ]
    
    print("Calling Groq...")
    resp = await client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.7, # slightly higher to encourage verbosity
        max_tokens=4000,
    )
    
    print(f"Total tokens: {resp.usage.total_tokens}")
    print(f"Prompt tokens: {resp.usage.prompt_tokens}")
    print(f"Completion tokens: {resp.usage.completion_tokens}")
    
    # Print the report size to give an idea
    report = resp.choices[0].message.content
    print(f"\nResponse preview (first 200 chars):\n{report[:200]}...")

if __name__ == "__main__":
    asyncio.run(main())
