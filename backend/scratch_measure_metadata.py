import asyncio
import os
import json
from dotenv import load_dotenv
from groq import AsyncGroq
from models.agent_schema import AgentReport, SceneProfile, VisibleText
from services.provider_router import AGENT_A_PROMPT

load_dotenv()

async def measure_payload(metadata: dict, label: str):
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
    
    text_prompt = f"Original Image Metadata:\n{json.dumps(metadata, indent=2)}\n\nScene Context Profile (from Agent 0):\n{scene_profile.model_dump_json(indent=2)}\n\nPlease provide your analysis strictly as a JSON object matching this schema:\n{json.dumps(AgentReport.model_json_schema(), indent=2)}"
    
    messages = [
        {"role": "system", "content": AGENT_A_PROMPT},
        {"role": "user", "content": text_prompt}
    ]
    
    resp = await client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=messages,
        max_tokens=10,
    )
    print(f"[{label}] Text Baseline Tokens: {resp.usage.prompt_tokens}")

async def main():
    metadata_light = {}
    
    metadata_heavy = {
        "Image Width": 4000,
        "Image Height": 3000,
        "Make": "Apple",
        "Model": "iPhone 15 Pro",
        "Software": "17.4.1",
        "DateTime": "2024:05:12 14:22:11",
        "GPSLatitudeRef": "N",
        "GPSLatitude": [37, 19, 43.2],
        "GPSLongitudeRef": "W",
        "GPSLongitude": [121, 57, 12.1],
        "GPSAltitudeRef": "\x00",
        "GPSAltitude": 12.3,
        "GPSTimeStamp": [14, 22, 11],
        "GPSImgDirectionRef": "T",
        "GPSImgDirection": 145.2,
        "ColorSpace": 1,
        "ExifImageWidth": 4000,
        "ExifImageHeight": 3000,
        "FocalLength": 6.86,
        "FNumber": 1.78,
        "ExposureTime": 0.008,
        "ISOSpeedRatings": 100,
        "ShutterSpeedValue": 6.9,
        "ApertureValue": 1.66,
        "BrightnessValue": 5.4,
        "ExposureBiasValue": 0.0,
        "SubjectArea": [2000, 1500, 500, 500],
        "LensSpecification": [2.2, 9.0, 1.78, 2.8],
        "LensMake": "Apple",
        "LensModel": "iPhone 15 Pro back triple camera 6.86mm f/1.78",
        "MakerNote": "Apple iOS... " * 100, # simulate a very large MakerNote tag
        "UserComment": "Edited in Lightroom... " * 20
    }
    
    await measure_payload(metadata_light, "Light Metadata")
    await measure_payload(metadata_heavy, "Heavy Metadata")

if __name__ == "__main__":
    asyncio.run(main())
