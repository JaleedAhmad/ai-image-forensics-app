import os
import json
import asyncio
from pathlib import Path
from PIL import Image
import sys
import io

# Add backend to path so we can import services
sys.path.append(str(Path(__file__).parent.parent))

from services.agent_0 import run_agent_0
from services.agent_a import run_agent_a
from services.agent_b import run_agent_b
from services.agent_c import run_agent_c
from main import get_ela_image, get_edge_map, scan_metadata

async def generate_real_fixtures():
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    image_path = Path(__file__).parent.parent.parent / "assets" / "dashboard.png"
    anomaly_path = Path(__file__).parent.parent.parent / "assets" / "anomaly.png"

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    ela_bytes = get_ela_image(pil_img)
    edge_bytes = get_edge_map(image_bytes)

    metadata_finding = scan_metadata(pil_img)
    metadata = {
        "format": getattr(pil_img, "format", "Unknown"),
        "size": pil_img.size,
        "mode": pil_img.mode,
    }
    if metadata_finding:
        metadata["scan_result"] = metadata_finding

    print("Generating SceneProfile - Agent 0...")
    try:
        scene_profile = await run_agent_0(image_bytes)
        with open(fixtures_dir / "scene_profile_success.json", "w") as f:
            f.write(scene_profile.model_dump_json(indent=2))
        print("Agent 0 capture successful.")
    except Exception as e:
        print(f"Agent 0 capture failed: {e}")
        scene_profile = None

    if not scene_profile:
        print("Skipping downstream agents due to Agent 0 failure.")
        return

    print("Generating Agent A Report...")
    try:
        report_a = await run_agent_a(image_bytes, ela_bytes, metadata, scene_profile)
        with open(fixtures_dir / "agent_a_success.json", "w") as f:
            f.write(report_a.model_dump_json(indent=2))
        print("Agent A capture successful.")
    except Exception as e:
        print(f"Agent A capture failed: {e}")
        report_a = None

    print("Generating Agent B Report (Authentic)...")
    try:
        report_b = await run_agent_b(image_bytes, edge_bytes, scene_profile)
        with open(fixtures_dir / "agent_b_success.json", "w") as f:
            f.write(report_b.model_dump_json(indent=2))
        print("Agent B capture successful.")
    except Exception as e:
        print(f"Agent B capture failed: {e}")
        report_b = None

    print("Generating Agent B Report (Anomalous)...")
    try:
        with open(anomaly_path, "rb") as f:
            anomaly_bytes = f.read()
        anomaly_edge_bytes = get_edge_map(anomaly_bytes)
        report_b_anomalous = await run_agent_b(anomaly_bytes, anomaly_edge_bytes, scene_profile)
        with open(fixtures_dir / "agent_b_anomalous.json", "w") as f:
            f.write(report_b_anomalous.model_dump_json(indent=2))
        print("Agent B (Anomalous) capture successful.")
    except Exception as e:
        print(f"Agent B (Anomalous) capture failed: {e}")

    if report_a and report_b:
        print("Generating Agent C Verdict...")
        try:
            verdict = await run_agent_c(report_a, report_b, scene_profile)
            with open(fixtures_dir / "arbitrator_verdict_normal.json", "w") as f:
                f.write(verdict.model_dump_json(indent=2))
            print("Agent C capture successful.")
        except Exception as e:
            print(f"Agent C capture failed: {e}")
    
    print("\nUpdating README.md with status...")
    readme_content = """# LLM Fixtures

These JSON files are used by the LLM mock mode (`USE_MOCK_LLM=true`) to enable testing without burning live API quota.

> **NOTE**: Some of these fixtures were captured from real API calls, while others may still be synthetic or missing if API quotas were exhausted during capture. See the latest commit history for details on which files are real.
"""
    with open(fixtures_dir / "README.md", "w") as f:
        f.write(readme_content)

if __name__ == "__main__":
    asyncio.run(generate_real_fixtures())
