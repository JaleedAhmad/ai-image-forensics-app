# LLM Fixtures

These JSON files are used by the LLM mock mode (`USE_MOCK_LLM=true`) to enable testing without burning live API quota.

## Capture Status (Last Run)

- **Agent 0 (Scene Profiler)**: Failed (429 RESOURCE_EXHAUSTED / 404 NOT_FOUND). The `scene_profile_success.json` is a generated blank profile.
- **Agent A (Metadata Analyst)**: Failed (429 RESOURCE_EXHAUSTED). The `agent_a_success.json` contains the fallback `agent_failure` report.
- **Agent B (Semantic Auditor)**: Failed (validation failure / model decommissioned). Both `agent_b_success.json` and `agent_b_anomalous.json` contain the fallback `agent_failure` report.
- **Agent C (Forensic Arbitrator)**: **SUCCESS** (`zai-glm-4.7`). The `arbitrator_verdict_normal.json` is a real API response from Cerebras successfully reasoning over the fallback reports of Agent A and Agent B.

> **NOTE**: Due to rate limits and model deprecations, most fixtures currently represent graceful failures. When API quotas reset, `capture_fixtures.py` can be run again to capture successful full-pipeline executions.
