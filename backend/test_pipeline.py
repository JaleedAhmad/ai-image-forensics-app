import asyncio
import os
import json
from PIL import Image
import io

from services.agent_0 import run_agent_0
from services.provider_router import run_vision_agents
from services.agent_c import run_agent_c

async def main():
    print("Generating complex synthetic image for test...")
    with open("../assets/anomaly.png", "rb") as f:
        img_bytes = f.read()

    print("Running Agent 0...")
    scene_profile = await run_agent_0(img_bytes)
    print("Agent 0 complete.")
    
    print("Running Vision Agents (A and B)...")
    metadata = {"Exposure": "1/200", "ISO": 100, "Software": "Adobe Photoshop"}
    report_a, report_b = await run_vision_agents(img_bytes, img_bytes, img_bytes, metadata, scene_profile)
    print("Vision Agents complete.")
    
    print("Running Agent C (Arbitrator)...")
    verdict = await run_agent_c(report_a, report_b, scene_profile)
    print("Pipeline Complete. Final Verdict:")
    print(verdict.model_dump_json(indent=2))

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
