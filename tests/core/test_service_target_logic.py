import pytest
from unittest.mock import MagicMock, patch
from core.engine import ChatEngine

@pytest.fixture
def mock_engine():
    with patch('core.engine.genai.Client') as mock_genai:
        mock_channel = MagicMock()
        engine = ChatEngine(
            channel=mock_channel,
            chat_name="TestGroup",
            task="Check dinner availability",
            api_key="fake_key"
        )
        # Manually attach the mock client so we can configure it in tests
        engine.client = mock_genai.return_value
        return engine

def test_build_prompt_with_single_service_target(mock_engine):
    """
    Test that the prompt correctly focuses on a single service target.
    """
    mock_engine.state["service_target"] = "Junyu"
    
    msgs = [{"sender": "Junyu", "text": "Help me check", "timestamp": "12:00"}]
    context_lines = ["[12:00] Junyu: Help me check"]
    
    prompt = mock_engine._build_prompt(msgs, context_lines)
    
    # Check if the service target is correctly injected into the "goal" section
    assert "為 **Junyu** 完成以下任務計畫" in prompt

def test_build_prompt_with_group_service_target(mock_engine):
    """
    Test that the prompt correctly focuses on the entire group.
    """
    mock_engine.state["service_target"] = "全體成員"
    
    msgs = [
        {"sender": "Member A", "text": "Where should we eat?", "timestamp": "12:00"},
        {"sender": "Member B", "text": "Any suggestions?", "timestamp": "12:01"}
    ]
    context_lines = [
        "[12:00] Member A: Where should we eat?",
        "[12:01] Member B: Any suggestions?"
    ]
    
    prompt = mock_engine._build_prompt(msgs, context_lines)
    
    # Check if the service target is correctly injected
    assert "為 **全體成員** 完成以下任務計畫" in prompt

@pytest.mark.asyncio
async def test_analyze_context_single_target(mock_engine):
    """
    Test that analyze_context correctly identifies a single person as the service target.
    """
    # Mock the GenAI client and its response
    mock_client = mock_engine.client
    mock_response = MagicMock()
    mock_response.text = '{"service_target": "Junyu", "task_start_time": "[12:00]", "is_started": true}'
    mock_client.models.generate_content.return_value = mock_response
    
    context_lines = ["[12:00] Junyu: I need help with X"]
    await mock_engine.analyze_context(context_lines)
    
    assert mock_engine.state["service_target"] == "Junyu"
    assert mock_engine.state["task_start_time"] == "[12:00]"

@pytest.mark.asyncio
async def test_analyze_context_group_target(mock_engine):
    """
    Test that analyze_context correctly identifies the group as the service target.
    """
    mock_client = mock_engine.client
    mock_response = MagicMock()
    mock_response.text = '{"service_target": "全體成員", "task_start_time": "[12:00]", "is_started": true}'
    mock_client.models.generate_content.return_value = mock_response
    
    context_lines = [
        "[12:00] Alice: Does anyone know the time?",
        "[12:01] Bob: I don't know."
    ]
    await mock_engine.analyze_context(context_lines)
    
    assert mock_engine.state["service_target"] == "全體成員"

@pytest.mark.asyncio
async def test_analyze_context_with_restart_intent_already_fulfilled(mock_engine):
    """
    Test that analyze_context correctly handles a scenario where a restart intent
    has already been fulfilled (is_started=True).
    """
    mock_client = mock_engine.client
    mock_response = MagicMock()
    # Simulate LLM identifying that the "Restart" action was already done at 11:15 PM
    mock_response.text = '{"service_target": "俊羽", "task_start_time": "[11:15 PM]", "is_started": true}'
    mock_client.models.generate_content.return_value = mock_response
    
    context_lines = [
        "[8:48 PM] User: 黑貓米克斯寫實",
        "[11:15 PM] Hermes: 您好，我是 俊羽 的 AI 代理。請問接下來您想生成什麼樣的圖片呢？"
    ]
    await mock_engine.analyze_context(context_lines)
    
    assert mock_engine.state["task_start_time"] == "[11:15 PM]"
    
    # Verify pruning logic in build_prompt
    msgs = []
    prompt = mock_engine._build_prompt(msgs, context_lines)
    
    # The prompt should start from the 11:15 PM message
    assert "[8:48 PM] User: 黑貓米克斯寫實" not in prompt
    assert "[11:15 PM] Hermes: 您好，我是 俊羽 的 AI 代理" in prompt
    # And because it's in the history, intro_already_done should be true
    assert "你已經在之前的對話中自我介紹過了" in prompt
