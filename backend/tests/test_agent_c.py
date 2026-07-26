import pytest
import asyncio
from unittest.mock import patch, MagicMock
from models.agent_schema import AgentReport, FinalVerdict, SceneProfile

# Import the module to test
import services.agent_c as agent_c

@pytest.fixture
def mock_agent_report_failed():
    return AgentReport(
        agent="metadata_analyst",
        thinking="Failed to analyze.",
        preliminary_verdict="uncertain",
        confidence=0.0,
        findings=[],
        artifact_locations=[],
        provider="test-provider",
        manipulation_indicators=0,
        authenticity_indicators=0,
        reasoning_summary="Failure."
    )

@pytest.fixture
def mock_agent_report_success():
    return AgentReport(
        agent="semantic_auditor",
        thinking="Successfully analyzed.",
        preliminary_verdict="authentic",
        confidence=0.95,
        findings=[],
        artifact_locations=[],
        provider="test-provider",
        manipulation_indicators=0,
        authenticity_indicators=5,
        reasoning_summary="Success."
    )

@pytest.fixture
def mock_scene_profile():
    return SceneProfile(
        medium="photograph",
        medium_confidence="high",
        medium_reasoning="Looks like a photo.",
        subject_description="Test",
        human_subjects_present=False,
        human_subject_notes="",
        lighting_and_physics_notes="Normal.",
        stylistic_elements_that_mimic_flaws=[],
        visible_text={"present": False, "transcription": "", "text_context": ""},
        setting="real_world_photographable",
        setting_notes="",
        image_quality_notes="Good.",
        flags_for_downstream_agents="None"
    )

@pytest.mark.asyncio
@patch('services.agent_c._call_cerebras')
@patch.dict('os.environ', {'CEREBRAS_API_KEY': 'fake-key'})
async def test_arbitrator_caps_confidence_on_degraded_input(mock_call_cerebras, mock_agent_report_failed, mock_agent_report_success, mock_scene_profile):
    # Mock verdict response with confidence=0.95, no failure acknowledgment
    mock_verdict = FinalVerdict(
        thinking="Agent B said authentic.",
        verdict="authentic",
        confidence=0.95,
        consensus="partial_agreement",
        agent_a_report=mock_agent_report_failed,
        agent_b_report=mock_agent_report_success,
        arbitrator_reasoning="I trust Agent B.",
        key_evidence=[],
        artifact_locations=[],
        providers_used=["mock-model"],
        degraded_mode=False
    )
    mock_call_cerebras.return_value = (mock_verdict.model_dump_json(), "mock-model")
    
    final_verdict = await agent_c.run_agent_c(mock_agent_report_failed, mock_agent_report_success, mock_scene_profile)
    
    # Assert final verdict.confidence <= DEGRADED_STATE_CONFIDENCE_CAP
    assert final_verdict.confidence <= agent_c.DEGRADED_STATE_CONFIDENCE_CAP
    # Assert final verdict.verdict == "uncertain"
    assert final_verdict.verdict == "uncertain"
    # Assert warning was added to reasoning
    assert "WARNING: The pipeline operated in a degraded state" in final_verdict.arbitrator_reasoning


@pytest.mark.asyncio
@patch('services.agent_c._call_cerebras')
@patch.dict('os.environ', {'CEREBRAS_API_KEY': 'fake-key'})
async def test_arbitrator_allows_override_with_acknowledgment(mock_call_cerebras, mock_agent_report_failed, mock_agent_report_success, mock_scene_profile):
    # Same degraded input, but reasoning text explicitly mentions "agent failure" and confidence >= 0.85
    mock_verdict = FinalVerdict(
        thinking="Agent B said authentic.",
        verdict="authentic",
        confidence=0.90,
        consensus="partial_agreement",
        agent_a_report=mock_agent_report_failed,
        agent_b_report=mock_agent_report_success,
        arbitrator_reasoning="Despite the agent failure, Agent B is absolutely certain.",
        key_evidence=[],
        artifact_locations=[],
        providers_used=["mock-model"],
        degraded_mode=False
    )
    mock_call_cerebras.return_value = (mock_verdict.model_dump_json(), "mock-model")
    
    final_verdict = await agent_c.run_agent_c(mock_agent_report_failed, mock_agent_report_success, mock_scene_profile)
    
    # Assert the cap is NOT applied
    assert final_verdict.confidence == 0.90
    assert final_verdict.verdict == "authentic"
    assert "WARNING: The pipeline operated in a degraded state" not in final_verdict.arbitrator_reasoning
