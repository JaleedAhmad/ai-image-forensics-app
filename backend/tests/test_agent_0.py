import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.agent_0 import run_agent_0
from models.agent_schema import SceneProfile, VisibleText

@pytest.mark.asyncio
async def test_agent_0_success():
    mock_profile = SceneProfile(
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

    class MockResponse:
        text = mock_profile.model_dump_json()

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=MockResponse())

    with patch('services.agent_0.genai.Client', return_value=mock_client):
        result = await run_agent_0(b"fake_image_bytes")
        assert result.medium == "photograph"
        assert result.subject_description == "A cat."

@pytest.mark.asyncio
async def test_agent_0_fallback():
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=Exception("API Error"))

    with patch('services.agent_0.genai.Client', return_value=mock_client):
        result = await run_agent_0(b"fake_image_bytes")
        assert result.medium == "unclear"
        assert result.medium_reasoning == "Profiling failed."
        assert mock_client.aio.models.generate_content.call_count == 2
