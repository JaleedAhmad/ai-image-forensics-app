import os
import logging
import asyncio
from google import genai
from google.genai import types
from models.agent_schema import SceneProfile, VisibleText

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_AGENT_0 = """You are a Scene Profiler for a forensic image-analysis pipeline. Your job is 
NOT to determine whether this image is AI-generated. Other specialized agents 
handle that. Your job is to describe the image accurately and neutrally so 
those agents can calibrate their analysis correctly.

Analyze the image and return a JSON object with the following fields. Be 
precise and literal — do not speculate about authenticity or generation 
method anywhere in this output.

{
  "medium": "One of: photograph, digital_painting, 3d_render, illustration, 
             anime_manga, screenshot_ui, screenshot_game, scanned_print, 
             vector_graphic, mixed_media, unclear",
  
  "medium_confidence": "high | medium | low",
  
  "medium_reasoning": "1-2 sentences on visual cues that led to this 
             classification (e.g., visible brushwork, render-typical lighting, 
             UI chrome elements, halftone dot pattern from print scanning).",
  
  "subject_description": "Detailed, neutral description of what's depicted: 
             主 subject(s), setting, composition, notable objects. 3-5 sentences.",
  
  "human_subjects_present": true/false,
  
  "human_subject_notes": "If true: count of people, and whether hands, teeth, 
             ears, or eyes are clearly visible and inspectable (these are 
             common AI failure points — flag their visibility, not their 
             correctness). If false: null.",
  
  "lighting_and_physics_notes": "Describe light source(s), shadow direction/
             consistency, and reflections if present. Note only — do not 
             judge plausibility.",
  
  "stylistic_elements_that_mimic_flaws": "List any elements that could look 
             like AI artifacts to an untrained eye but are normal for this 
             medium/style — e.g., intentional distortion in an illustration, 
             motion blur, deliberate asymmetry, glitch-art aesthetic, JPEG 
             compression from repeated re-uploads. Empty list if none.",
  
  "visible_text": {
    "present": true/false,
    "transcription": "Verbatim transcription of ALL visible text, including 
             signage, labels, screens-within-the-image, watermarks. Preserve 
             exact spelling/spacing as shown, even if it looks wrong. If no 
             text, empty string.",
    "text_context": "Where the text appears and what it's on (e.g., 'street 
             sign in background', 'text overlaid by uploader', 'label on 
             product packaging')."
  },
  
  "setting": "real_world_photographable | fictional_or_impossible | 
             ambiguous",
  
  "setting_notes": "Brief note if fictional_or_impossible or ambiguous — 
             what makes it so.",
  
  "image_quality_notes": "Resolution impression, compression artifacts, 
             noise level, upscaling indicators — purely descriptive, not 
             diagnostic.",
  
  "flags_for_downstream_agents": "Anything else Agent A or Agent B should 
             know before analyzing this image that isn't captured above. 
             Empty string if nothing."
}

Rules:
- Output ONLY the JSON object. No preamble, no markdown code fences, no 
  explanation outside the JSON.
- If you are uncertain about a field, say so within the field rather than 
  guessing silently (e.g., medium_confidence: "low").
- Do not use the words "AI-generated," "fake," "authentic," or "real" 
  anywhere in your output — that determination belongs to other agents. 
  Your role is strictly descriptive.
- If the image contains nothing legible as text, visible_text.transcription 
  must be an empty string, not "N/A" or similar.
"""

def get_blank_profile() -> SceneProfile:
    return SceneProfile(
        medium="unclear",
        medium_confidence="low",
        medium_reasoning="Profiling failed.",
        subject_description="Unknown subject due to profiling failure.",
        human_subjects_present=False,
        human_subject_notes=None,
        lighting_and_physics_notes="Unknown",
        stylistic_elements_that_mimic_flaws="Unknown",
        visible_text=VisibleText(present=False, transcription="", text_context=""),
        setting="ambiguous",
        setting_notes="Profiling failed.",
        image_quality_notes="Unknown",
        flags_for_downstream_agents="Agent 0 profiling failed. Proceed without scene context."
    )

async def run_agent_0(original_image_bytes: bytes) -> SceneProfile:
    model_name = "gemini-2.5-flash"
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"), http_options={"api_version": "v1beta"}
    )

    parts = [
        types.Part.from_bytes(data=original_image_bytes, mime_type="image/jpeg"),
        "Analyze this image and return the required SceneProfile JSON.",
    ]

    async def call():
        return await client.aio.models.generate_content(
            model=model_name,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_AGENT_0,
                response_mime_type="application/json",
                response_schema=SceneProfile,
                temperature=0.0,
            ),
        )

    for attempt in range(2):
        try:
            # 20s timeout per attempt
            response = await asyncio.wait_for(call(), timeout=20.0)
            return SceneProfile.model_validate_json(response.text)
        except Exception as e:
            if attempt == 0:
                logger.warning(f"Agent 0 encountered an error on attempt 1: {e}. Retrying in 1s...")
                await asyncio.sleep(1.0)
            else:
                logger.error(f"Agent 0 encountered a total failure after retries: {e}")
                return get_blank_profile()
