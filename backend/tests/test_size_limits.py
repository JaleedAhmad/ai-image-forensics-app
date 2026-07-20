import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from PIL import Image
import io

from services.agent_b import _resize_for_token_budget
from services.provider_router import _fallback_agent_a_on_groq
from models.agent_schema import SceneProfile, VisibleText

def create_test_image_bytes(width, height):
    img = Image.new('RGB', (width, height), color='red')
    out = io.BytesIO()
    img.save(out, format='JPEG')
    return out.getvalue()

def test_agent_b_resizer_fits_token_budget():
    # A large image that would exceed the 1500 token budget.
    # Empirical max pixels for 1500 tokens is ~1,561,686
    # Let's create an image that is 2000x2000 (4,000,000 pixels)
    large_image_bytes = create_test_image_bytes(2000, 2000)
    
    resized_bytes = _resize_for_token_budget(large_image_bytes)
    
    with Image.open(io.BytesIO(resized_bytes)) as img:
        pixels = img.width * img.height
        
    # The resizer should bring the pixel count under 1,561,686 roughly.
    assert pixels <= 1561686 + 1000 # Allow slight rounding error
    
    # Let's also check an image that is already small.
    small_image_bytes = create_test_image_bytes(800, 800) # 640,000 pixels
    resized_small_bytes = _resize_for_token_budget(small_image_bytes)
    
    with Image.open(io.BytesIO(resized_small_bytes)) as img:
        pixels_small = img.width * img.height
    
    # It should not resize the small image.
    assert pixels_small == 800 * 800

@pytest.mark.asyncio
async def test_agent_a_fallback_aborts_on_large_image():
    # Create two large images that combined will easily exceed 3000 tokens.
    # 2000x2000 = 4M pixels per image. 8M pixels total.
    large_orig = create_test_image_bytes(2000, 2000)
    large_ela = create_test_image_bytes(2000, 2000)
    
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
    
    metadata = {}
    
    # We patch the actual call to groq to ensure it is NEVER called.
    with patch('services.provider_router.AsyncGroq') as MockGroq:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        MockGroq.return_value = mock_client
        
        report = await _fallback_agent_a_on_groq(large_orig, large_ela, metadata, scene_profile)
        
        # Verify the call was short-circuited and an agent_failure was returned.
        assert report.confidence == 0.0
        assert report.preliminary_verdict == "uncertain"
        assert report.agent == "metadata_analyst"
        assert len(report.findings) == 1
        assert report.findings[0].type == "agent_failure"
        assert "Image too large for Groq fallback" in report.findings[0].description
