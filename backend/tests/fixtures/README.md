# LLM Fixtures

These JSON files are used by the LLM mock mode (`USE_MOCK_LLM=true`) to enable testing without burning live API quota.

> **IMPORTANT**: Due to immediate `429 RESOURCE_EXHAUSTED` quotas on both Gemini and Groq at the time of creation, these fixtures were generated synthetically using Pydantic instantiation to ensure schema validity.
>
> **TODO**: Once API quotas reset, replace `scene_profile_success.json`, `agent_a_success.json`, `agent_b_success.json`, `agent_b_anomalous.json`, and `arbitrator_verdict_normal.json` with **real captured responses** from actual API calls to ensure maximum fidelity.
