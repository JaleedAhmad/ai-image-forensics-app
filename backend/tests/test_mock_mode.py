import os
import json
import pytest
from pathlib import Path

from models.agent_schema import SceneProfile, AgentReport, FinalVerdict
from services.mock_llm import get_mock_response

@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"

def test_fixtures_are_schema_valid(fixtures_dir):
    """
    Validates every synthetic fixture against the actual Pydantic schemas.
    This confirms the fixtures are schema-correct, even though they were generated synthetically.
    """
    # SceneProfile fixtures
    with open(fixtures_dir / "scene_profile_success.json", "r") as f:
        SceneProfile.model_validate_json(f.read())
        
    with open(fixtures_dir / "scene_profile_blank.json", "r") as f:
        SceneProfile.model_validate_json(f.read())

    # AgentReport fixtures
    for report_file in ["agent_a_success.json", "agent_b_success.json", "agent_b_anomalous.json"]:
        with open(fixtures_dir / report_file, "r") as f:
            AgentReport.model_validate_json(f.read())
            
    # FinalVerdict fixtures
    for verdict_file in ["arbitrator_verdict_normal.json", "arbitrator_verdict_degraded.json"]:
        with open(fixtures_dir / verdict_file, "r") as f:
            FinalVerdict.model_validate_json(f.read())
            
    # Explicitly verify the intentionally broken ones fail parsing
    for broken_file in ["agent_a_validation_failure.json", "agent_b_validation_failure.json"]:
        with open(fixtures_dir / broken_file, "r") as f:
            with pytest.raises(Exception):
                AgentReport.model_validate_json(f.read())

def test_mock_llm_routing_logic(monkeypatch):
    """
    Test that mock_llm.py correctly routes scenarios and raises errors in production.
    """
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("MOCK_SCENARIO", "clean")
    
    # Authentic clean scenario
    response = get_mock_response("scene_profiler")
    assert "vector_graphic" in response
    
    response_b = get_mock_response("semantic_auditor")
    report = AgentReport.model_validate_json(response_b)
    assert report.confidence == 0.95
    assert report.findings[0].severity == "none"

    # Anomalous scenario
    monkeypatch.setenv("MOCK_SCENARIO", "anomalous")
    response_anomalous = get_mock_response("semantic_auditor")
    report_anomalous = AgentReport.model_validate_json(response_anomalous)
    assert report_anomalous.preliminary_verdict == "manipulated"
    assert report_anomalous.findings[0].severity == "critical"
    
    # Retry success statefulness test
    monkeypatch.setenv("MOCK_SCENARIO", "retry_success")
    import services.mock_llm
    services.mock_llm._validation_failure_counts["agent_a"] = 0
    fail_res = get_mock_response("metadata_analyst")
    assert "invalid_json" not in fail_res  # We don't return invalid_json dict string, we load the file
    with pytest.raises(Exception):
        AgentReport.model_validate_json(fail_res)
        
    success_res = get_mock_response("metadata_analyst")
    AgentReport.model_validate_json(success_res)

def test_mock_llm_production_failsafe(monkeypatch):
    """
    Test that mock mode strictly refuses to run if it detects a production environment.
    """
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("SPACE_ID", "some-huggingface-space-id")
    
    with pytest.raises(RuntimeError, match="CRITICAL SECURITY ERROR"):
        get_mock_response("scene_profiler")
