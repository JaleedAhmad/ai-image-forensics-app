import asyncio
import httpx
import sys

async def test_image(image_path: str, label: str):
    print(f"--- Running {label} on {image_path} ---")
    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(image_path, "rb") as f:
            files = {"file": (image_path.split('/')[-1], f, "image/png")}
            async with client.stream("POST", "http://localhost:8000/analyze_image/", files=files) as response:
                if response.status_code != 200:
                    print(f"Error {response.status_code}")
                    return
                
                final_data = None
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json
                        try:
                            data = json.loads(line[6:])
                            print(f"Stage: {data.get('stage')}")
                            if data.get('stage') == 'verdict_ready':
                                final_data = data
                        except Exception as e:
                            pass
                            
            if not final_data:
                print("Failed to get final result")
                return
                
            agent_a = final_data.get("agent_a_report", {})
            agent_b = final_data.get("agent_b_report", {})
            print("Raw Agent A:", agent_a)
            print("Raw Agent B:", agent_b)
            
            print(f"Agent A findings: {len(agent_a.get('findings', []))} (Verdict: {agent_a.get('preliminary_verdict')})")
            for f in agent_a.get('findings', []):
                print(f" - [{f.get('severity')}] {f.get('type')}: {f.get('description')}")
                
            print(f"Agent B findings: {len(agent_b.get('findings', []))} (Verdict: {agent_b.get('preliminary_verdict')})")
            for f in agent_b.get('findings', []):
                print(f" - [{f.get('severity')}] {f.get('type')}: {f.get('description')}")
                
if __name__ == "__main__":
    asyncio.run(test_image("/home/noir/ai-image-forensics-app/assets/dashboard.png", "TEST 2: Complex Image"))
