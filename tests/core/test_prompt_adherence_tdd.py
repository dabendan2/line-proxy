import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from core.engine import ChatEngine
from channels.base import BaseChannel

@pytest.mark.asyncio
async def test_image_gen_exact_prompt_adherence():
    """
    Test that when a task explicitly provides a prompt (e.g. within quotes or as a direct requirement),
    the AI engine correctly extracts and passes it to the image_gen tool WITHOUT altering it.
    
    This follows the TDD 'Strict Red Phase': this test is expected to FAIL because the 
    current engine prompt/logic allows the AI to 'expand' or 'optimize' the query.
    """
    
    # 1. Setup Mock Channel
    mock_channel = MagicMock(spec=BaseChannel)
    mock_channel.extract_messages = AsyncMock(return_value=[
        {"sender": "User", "text": "OK, here is the cat photo.", "timestamp": "10:00 PM"}
    ])
    mock_channel.select_chat = AsyncMock(return_value={"status": "success"})
    mock_channel.bring_to_front = AsyncMock()
    mock_channel.send_message = AsyncMock()
    mock_channel.send_image = AsyncMock()

    # 2. Define the Task with a specific prompt requirement
    exact_prompt = "這是我家貓咪, 3歲,女生。如果是人類的話,她會長怎麼樣呢?請生成圖片。"
    task_desc = f"對方已提供貓咪照片。請使用以下精確提詞生成擬人圖：'{exact_prompt}'"

    # 3. Setup Engine with Sequential AI Responses
    with patch('google.genai.Client') as mock_genai_cls:
        mock_client = mock_genai_cls.return_value
        
        # turn 1: AI calls the tool with the EXACT prompt
        resp1 = MagicMock()
        resp1.text = f'[TOOL_ACCESS_NEEDED, tool="image_gen", query="{exact_prompt}"]'
        
        # turn 2: AI finishes
        resp2 = MagicMock()
        resp2.text = '[CONVERSATION_ENDED, summary="Done"]'
        
        # Set the side effect to return these responses in sequence
        mock_client.models.generate_content.side_effect = [resp1, resp2]

        engine = ChatEngine(channel=mock_channel, chat_name="TestChat", task=task_desc, api_key="fake_key")
        
        # We want to intercept the call to _generate_image_locally to check the 'query' argument
        with patch.object(engine, '_generate_image_locally', new_callable=AsyncMock) as mock_local_gen:
            mock_local_gen.return_value = "/tmp/fake_image.png"
            
            # 4. Run the Engine loop once (or trigger the specific logic)
            # generate_and_send_reply is the core logic that parses the AI response and calls tools
            await engine.generate_and_send_reply(mock_channel.extract_messages.return_value)

            # 5. Assertions (The Verification)
            # We expect the tool to be called with EXACTLY the prompt provided in the task.
            # Current logic will fail this because the AI will 'summarize' or 'translate' the prompt.
            assert mock_local_gen.called, "Image generation tool was not called."
            actual_query = mock_local_gen.call_args[0][0]
            
            assert actual_query == exact_prompt, f"AI altered the prompt!\nExpected: {exact_prompt}\nActual: {actual_query}"
