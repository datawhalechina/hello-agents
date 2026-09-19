import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.forum_scheduler import ForumScheduler

@pytest.mark.asyncio
async def test_push_user_message():
    scheduler = ForumScheduler()
    forum_id = 999
    
    # 1. Test pushing message
    await scheduler.push_user_message(forum_id, "TestUser", "Hello World")
    
    assert forum_id in scheduler.user_message_queues
    queue = scheduler.user_message_queues[forum_id]
    assert queue.qsize() == 1
    
    item = await queue.get()
    assert item["speaker"] == "TestUser"
    assert item["content"] == "Hello World"
    assert "timestamp" in item

@pytest.mark.asyncio
async def test_process_user_messages_empty():
    scheduler = ForumScheduler()
    processed = await scheduler._process_user_messages(123)
    assert processed is False

@pytest.mark.asyncio
@patch("app.services.forum_scheduler.create_message")
@patch("app.services.forum_scheduler.manager.broadcast")
@patch("app.services.forum_scheduler.db_manager.get_connection")
async def test_process_user_messages_flow(mock_get_conn, mock_broadcast, mock_create_msg):
    # Setup Mocks
    mock_db = MagicMock()
    mock_get_conn.return_value = mock_db
    mock_db.close = MagicMock()
    
    # Mock create_message return value
    mock_msg = MagicMock()
    mock_msg.id = 1001
    mock_create_msg.return_value = mock_msg
    
    scheduler = ForumScheduler()
    forum_id = 888
    
    # Push a message
    await scheduler.push_user_message(forum_id, "Audience1", "Interruption!")
    
    # Process
    # We need to mock _broadcast_system_log too or let it run (it uses manager.broadcast)
    # But _broadcast_system_log calls create_task for persist_bg, which might fail without real Redis/DB
    # So let's patch _broadcast_system_log
    
    with patch.object(scheduler, '_broadcast_system_log', new_callable=AsyncMock) as mock_sys_log:
        processed = await scheduler._process_user_messages(forum_id)
        
        assert processed is True
        assert scheduler.user_message_queues[forum_id].empty()
        
        # Verify DB insert called
        assert mock_create_msg.call_count == 1
        call_args = mock_create_msg.call_args[0]
        assert call_args[1].speaker_name == "Audience1"
        assert call_args[1].content == "Interruption!"
        
        # Verify Broadcast called
        # _broadcast_message calls manager.broadcast
        assert mock_broadcast.called
        
        # Verify System Log
        assert mock_sys_log.called
        assert "观众 [Audience1] 发言" in mock_sys_log.call_args[0][1]
