import asyncio
import os
import json
from dotenv import load_dotenv
from groq import AsyncGroq
from models.agent_schema import AgentReport, SceneProfile, VisibleText
from services.provider_router import AGENT_A_PROMPT

load_dotenv()

async def measure_baseline():
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
    
    # Simulate a moderately dense EXIF metadata payload typical of a digital image
    sample_metadata = {
        "Image Width": 1366,
        "Image Height": 2019,
        "Compression": "JPEG (old-style)",
        "Make": "SONY",
        "Model": "ILCE-7M3",
        "Software": "Adobe Photoshop 2024",
        "DateTime": "2024:05:12 14:22:11",
        "ExifOffset": 216,
        "ColorSpace": 1,
        "ExifImageWidth": 1366,
        "ExifImageHeight": 2019,
        "FocalLength": 50.0,
        "FNumber": 1.8,
        "ExposureTime": 0.002,
        "ISOSpeedRatings": 100
    }
    
    text_prompt = f"Original Image Metadata:\n{json.dumps(sample_metadata, indent=2)}\n\nScene Context Profile (from Agent 0):\n{scene_profile.model_dump_json(indent=2)}\n\nPlease provide your analysis strictly as a JSON object matching this schema:\n{json.dumps(AgentReport.model_json_schema(), indent=2)}"
    
    messages = [
        {"role": "system", "content": AGENT_A_PROMPT},
        {"role": "user", "content": text_prompt}
    ]
    
    resp = await client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=messages,
        max_tokens=10,
    )
    print(f"Measured Text Baseline Tokens: {resp.usage.prompt_tokens}")

if __name__ == "__main__":
    asyncio.run(measure_baseline())
