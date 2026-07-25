import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Track how many times a validation failure has been returned so we can simulate retry success/failure
_validation_failure_counts = {
    "agent_a": 0,
    "agent_b": 0,
}

def get_mock_response(agent_name: str, fallback: bool = False) -> str:
    """
    Returns the string content of a JSON fixture based on the requested agent and MOCK_SCENARIO.
    If USE_MOCK_LLM is enabled but we are in production, it strictly raises an error.
    """
    if os.environ.get("SPACE_ID") or os.environ.get("ENVIRONMENT") == "production":
        raise RuntimeError("CRITICAL SECURITY ERROR: USE_MOCK_LLM is enabled in a production/HF Space environment! Refusing to start.")

    scenario = os.environ.get("MOCK_SCENARIO", "clean").lower()
    
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    
    # Helper to load a file
    def load(filename: str) -> str:
        path = fixtures_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Mock fixture not found: {path}")
        with open(path, "r") as f:
            return f.read()

    if agent_name == "scene_profiler":
        if scenario in ["agent_0_fail", "both_fail"]:
            # If we want a total failure, we simulate the LLM just returning garbage repeatedly
            # Agent 0 will retry and then fall back to get_blank_profile itself
            return '{"invalid_json": true' 
        return load("scene_profile_success.json")
        
    elif agent_name == "metadata_analyst":
        if scenario == "agent_a_fail":
            return '{"invalid_json": true' 
        elif scenario == "both_fail":
            return '{"invalid_json": true' 
        elif scenario == "retry_success":
            if _validation_failure_counts["agent_a"] == 0:
                _validation_failure_counts["agent_a"] += 1
                return load("agent_a_validation_failure.json")
            else:
                return load("agent_a_success.json")
        elif scenario == "retry_fail":
            return load("agent_a_validation_failure.json")
        else:
            return load("agent_a_success.json")
            
    elif agent_name == "semantic_auditor":
        if scenario == "anomalous":
            return load("agent_b_anomalous.json")
        elif scenario == "agent_b_fail" or scenario == "both_fail":
            return '{"invalid_json": true' 
        elif scenario == "retry_success":
            if _validation_failure_counts["agent_b"] == 0:
                _validation_failure_counts["agent_b"] += 1
                return load("agent_b_validation_failure.json")
            else:
                return load("agent_b_success.json")
        elif scenario == "retry_fail":
            return load("agent_b_validation_failure.json")
        else:
            return load("agent_b_success.json")
            
    elif agent_name == "arbitrator":
        if scenario in ["agent_a_fail", "agent_b_fail", "both_fail", "retry_fail"]:
            return load("arbitrator_verdict_degraded.json")
        else:
            return load("arbitrator_verdict_normal.json")
            
    raise ValueError(f"Unknown agent requested for mock: {agent_name}")
