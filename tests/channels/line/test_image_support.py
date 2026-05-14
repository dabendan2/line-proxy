import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from channels.line import driver as line_utils
from core.engine import LineProxyEngine

def test_parse_response_with_image():
    engine = LineProxyEngine(page=None, chat_name="Test", task="Test Task")
    
    # Single image
    resp = engine._parse_response("Here is the image [IMAGE, /path/to/img.jpg] [WAIT_FOR_USER_INPUT]")
    assert resp["text"] == "Here is the image"
    assert resp["images"] == ["/path/to/img.jpg"]
    assert resp["is_waiting"] is True
    
    # Multiple images
    resp = engine._parse_response("Multiple images [IMAGE, img1.png] and [IMAGE, img2.jpg]")
    assert resp["text"] == "Multiple images  and"
    assert resp["images"] == ["img1.png", "img2.jpg"]
    
    # URL image
    resp = engine._parse_response("Check this out [IMAGE, https://example.com/pic.png]")
    assert resp["images"] == ["https://example.com/pic.png"]

@pytest.mark.asyncio
async def test_generate_and_send_reply_with_image():
    # Mock page and history
    mock_page = MagicMock()
    mock_history = MagicMock()
    mock_history.get_full_context.return_value = ["User: Hello"]
    
    # Create engine with mocked components
    engine = LineProxyEngine(page=mock_page, chat_name="Test", task="Test Task")
    engine.history = mock_history
    engine.client = MagicMock()
    
    # Mock AI response
    mock_ai_resp = MagicMock()
    mock_ai_resp.text = "Look at this [IMAGE, /tmp/test.jpg] [WAIT_FOR_USER_INPUT]"
    engine.client.models.generate_content.return_value = mock_ai_resp
    
    with patch("channels.line.driver.send_message") as mock_send_msg, \
         patch("channels.line.driver.send_image") as mock_send_img:
        
        await engine.generate_and_send_reply([])
        
        # Verify message sent
        mock_send_msg.assert_called_once_with(mock_page, "Look at this")
        # Verify image sent
        mock_send_img.assert_called_once_with(mock_page, "/tmp/test.jpg")
        # Verify state updated
        assert "Look at this" in engine.state["sent_messages"]
        assert "[IMAGE: /tmp/test.jpg]" in engine.state["sent_messages"]

@pytest.mark.asyncio
async def test_ai_outputs_image_tag_when_asked():
    """Integration test to ensure the AI actually uses the [IMAGE, ...] tag when appropriate."""
    # Note: This requires a valid API key and internet access.
    # We'll use a specific task that strongly implies sending an image.
    engine = LineProxyEngine(
        page=MagicMock(), 
        chat_name="Test", 
        task="對方想要看我的工作證截圖，截圖放在 /home/ubuntu/id_card.png，請傳送給他。"
    )
    
    # We don't want to actually send anything, just check the parsed response
    context = ["對方: 請問可以看一下你的工作證嗎？"]
    prompt = engine._build_prompt(context)
    
    # We call the real AI here
    response = engine.client.models.generate_content(model=engine.model_name, contents=prompt)
    result = engine._parse_response(str(getattr(response, 'text', '')).strip())
    
    # Assertions
    assert "/home/ubuntu/id_card.png" in result["images"]
    print(f"AI Response: {getattr(response, 'text', '')}")
