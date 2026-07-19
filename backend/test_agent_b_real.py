import asyncio
import os
import json
from PIL import Image
import io
import sys

from services.agent_b import run_agent_b
from models.agent_schema import SceneProfile

async def main():
    # Use an empty or minimal image
    img = Image.new('RGB', (100, 100), color = 'red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    original_bytes = img_byte_arr.getvalue()
    
    edge_map = Image.new('L', (100, 100), color = 0)
    edge_map_byte_arr = io.BytesIO()
    edge_map.save(edge_map_byte_arr, format='JPEG')
    edge_bytes = edge_map_byte_arr.getvalue()

    scene_profile = SceneProfile(
        medium="photograph",
        medium_confidence="high",
        medium_reasoning="Looks like a photo",
        subject_description="None",
        human_subjects_present=False,
        human_subject_notes="None",
        lighting_and_physics_notes="None",
        stylistic_elements_that_mimic_flaws=[],
        visible_text={"present": False, "transcription": "", "text_context": ""},
        setting="real_world_photographable",
        setting_notes="None",
        image_quality_notes="None",
        flags_for_downstream_agents="None"
    )

    print("Running Agent B...")
    try:
        report = await run_agent_b(original_bytes, edge_bytes, scene_profile)
        print("Success!")
        print(report.model_dump_json(indent=2))
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
