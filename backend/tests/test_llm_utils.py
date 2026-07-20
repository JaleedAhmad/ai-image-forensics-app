import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel, ValidationError

from services.llm_utils import call_llm_with_json_validation
from models.agent_schema import AgentReport, AgentFinding

class MockGroqMessage:
    def __init__(self, content):
        self.content = content

class MockGroqChoice:
    def __init__(self, content):
        self.message = MockGroqMessage(content)

class MockGroqResponse:
    def __init__(self, content, model="mock-model"):
        self.choices = [MockGroqChoice(content)]
        self.model = model

class MockGeminiResponse:
    def __init__(self, text, model="mock-model"):
        self.text = text
        self.model = model

@pytest.fixture
def valid_report_json():
    return json.dumps({
        "thinking": "Test reasoning.",
        "agent": "metadata_analyst",
        "provider": "mock-model",
        "findings": [],
        "manipulation_indicators": 0,
        "authenticity_indicators": 0,
        "confidence": 0.9,
        "preliminary_verdict": "authentic",
        "reasoning_summary": "Test summary."
    })

@pytest.fixture
def invalid_report_json():
    return '{"thinking": "Missing required fields."}'

@pytest.mark.asyncio
async def test_llm_utils_groq_success(valid_report_json):
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=MockGroqResponse(valid_report_json))
    
    messages = [{"role": "user", "content": "test"}]
    
    report = await call_llm_with_json_validation(
        provider="groq",
        client=mock_client,
        model_name="test-groq",
        system_prompt="test",
        payload=messages,
        schema=AgentReport,
        agent_name="metadata_analyst",
        max_retries=1
    )
    
    assert report.confidence == 0.9
    assert report.preliminary_verdict == "authentic"
    assert mock_client.chat.completions.create.call_count == 1

@pytest.mark.asyncio
async def test_llm_utils_groq_retry_success(valid_report_json, invalid_report_json):
    mock_client = MagicMock()
    # First call returns invalid, second returns valid
    mock_client.chat.completions.create = AsyncMock(side_effect=[
        MockGroqResponse(invalid_report_json),
        MockGroqResponse(valid_report_json)
    ])
    
    messages = [{"role": "user", "content": "test"}]
    
    report = await call_llm_with_json_validation(
        provider="groq",
        client=mock_client,
        model_name="test-groq",
        system_prompt="test",
        payload=messages,
        schema=AgentReport,
        agent_name="metadata_analyst",
        max_retries=1
    )
    
    assert report.confidence == 0.9
    assert mock_client.chat.completions.create.call_count == 2
    
    # Check that the second call contained the retry prompt
    call_args = mock_client.chat.completions.create.call_args_list[1][1]
    sent_messages = call_args["messages"]
    assert len(sent_messages) == 3 # original + assistant + user retry
    assert sent_messages[-1]["role"] == "user"
    assert "Your previous response failed validation" in sent_messages[-1]["content"]

@pytest.mark.asyncio
async def test_llm_utils_gemini_success(valid_report_json):
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=MockGeminiResponse(valid_report_json))
    
    contents = ["test"]
    
    report = await call_llm_with_json_validation(
        provider="gemini",
        client=mock_client,
        model_name="test-gemini",
        system_prompt="test",
        payload=contents,
        schema=AgentReport,
        agent_name="metadata_analyst",
        max_retries=1
    )
    
    assert report.confidence == 0.9
    assert mock_client.aio.models.generate_content.call_count == 1

@pytest.mark.asyncio
async def test_llm_utils_total_failure():
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API is down"))
    
    messages = [{"role": "user", "content": "test"}]
    
    report = await call_llm_with_json_validation(
        provider="groq",
        client=mock_client,
        model_name="test-groq",
        system_prompt="test",
        payload=messages,
        schema=AgentReport,
        agent_name="metadata_analyst",
        max_retries=1
    )
    
    # Check the fallback object
    assert report.confidence == 0.0
    assert report.preliminary_verdict == "uncertain"
    assert report.agent == "metadata_analyst"
    assert len(report.findings) == 1
    assert report.findings[0].type == "agent_failure"
    assert "Metadata Analyst failed to generate a valid report: API is down" in report.findings[0].description
