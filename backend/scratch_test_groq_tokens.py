import asyncio
import os
import io
import base64
from PIL import Image
from groq import AsyncGroq
from dotenv import load_dotenv
load_dotenv()

async def test_tokens(width, height, num_images):
    client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
    img = Image.new('RGB', (width, height), color='red')
    out = io.BytesIO()
    img.save(out, format='JPEG', quality=95)
    img_b64 = base64.b64encode(out.getvalue()).decode()
    
    content = [{"type": "text", "text": "What is in this image?"}]
    for _ in range(num_images):
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
        
    messages = [{"role": "user", "content": content}]
    
    try:
        resp = await client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=messages,
            max_tokens=10,
        )
        print(f"Size: {width}x{height}, Images: {num_images}, Prompt Tokens: {resp.usage.prompt_tokens}")
    except Exception as e:
        print(f"Size: {width}x{height}, Images: {num_images}, Error: {e}")

async def main():
    await test_tokens(512, 512, 1)
    await test_tokens(512, 512, 2)
    await test_tokens(1024, 1024, 1)
    await test_tokens(1024, 1024, 2)
    await test_tokens(1366, 2019, 1)
    await test_tokens(1366, 2019, 2)

if __name__ == "__main__":
    asyncio.run(main())
