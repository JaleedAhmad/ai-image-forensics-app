import pytest
from pydantic import ValidationError
from models.agent_schema import AgentReport, AgentFinding

def test_agent_schema_accepts_none_severity():
    finding = AgentFinding(
        type="authenticity_marker",
        severity="none",
        description="Confirmed clean vector lines."
    )
    
    assert finding.severity == "none"
    
    report_data = {
        "thinking": "No anomalies found.",
        "agent": "semantic_auditor",
        "provider": "qwen/qwen3.6-27b",
        "findings": [
            {
                "type": "authenticity_marker",
                "severity": "none",
                "description": "Consistent lighting.",
                "location": None
            }
        ],
        "manipulation_indicators": 0,
        "authenticity_indicators": 1,
        "confidence": 0.95,
        "preliminary_verdict": "authentic",
        "reasoning_summary": "Image is authentic."
    }
    
    report = AgentReport.model_validate(report_data)
    assert len(report.findings) == 1
    assert report.findings[0].severity == "none"

def test_agent_schema_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        AgentFinding(
            type="anomaly",
            severity="invalid_level", # type: ignore
            description="Should fail."
        )
