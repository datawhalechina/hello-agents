import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys

# Mock missing dependencies
sys.modules['libsql_client'] = MagicMock()

import asyncio
from datetime import datetime, timezone
from app.services.forum_scheduler import ForumScheduler
from app.agent.agent import ParticipantAgent

class TestSchedulerRobustness(unittest.IsolatedAsyncioTestCase):
    async def test_error_broadcasting(self):
        scheduler = ForumScheduler()
        forum_id = 1
        
        # Mock dependencies
        mock_db = MagicMock()
        mock_forum = MagicMock()
        mock_forum.id = forum_id
        mock_forum.status = "running"
        mock_forum.duration_minutes = 10
        mock_forum.start_time = datetime.now(timezone.utc)
        mock_forum.moderator = None
        mock_forum.summary_history = []
        
        # Mock participant
        p1 = MagicMock()
        p1.persona.name = "Alice"
        p1.persona.system_prompt = "sys"
        p1.persona_id = 101
        
        # Mock Agent
        mock_agent = MagicMock(spec=ParticipantAgent)
        mock_agent.name = "Alice"
        mock_agent.private_memory = MagicMock()
        mock_agent.private_memory.speech_history = []
        mock_agent.ablation_flags = {}
        
        # Mock think to succeed
        mock_agent.think.return_value = {
            "action": "apply_to_speak",
            "mind": "I want to speak",
            "previous": "None",
            "benefit": "Insight"
        }
        
        # Mock speak to RAISE EXCEPTION
        async def mock_speak_error(*args, **kwargs):
            raise Exception("API Timeout")
        
        # Note: speak is called via asyncio.to_thread, so it should be a sync function or mocked such that to_thread handles it.
        # But here we mock to_thread or the method itself?
        # In the code: await asyncio.to_thread(agent.speak, ...)
        # So agent.speak should be a sync function that raises.
        def mock_speak_sync_error(*args, **kwargs):
            raise Exception("API Timeout")
        
        mock_agent.speak.side_effect = mock_speak_sync_error

        with patch('app.services.forum_scheduler.db_manager.get_connection', return_value=mock_db), \
             patch('app.services.forum_scheduler.get_forum', side_effect=[mock_forum, mock_forum, None]), \
             patch('app.services.forum_scheduler.get_forum_participants', return_value=[p1]), \
             patch('app.services.forum_scheduler.get_forum_messages', return_value=[]), \
             patch('app.services.forum_scheduler.update_forum'), \
             patch('app.services.forum_scheduler.update_forum_participant'), \
             patch('app.services.forum_scheduler.create_message'), \
             patch('app.services.forum_scheduler.manager') as mock_manager, \
             patch('asyncio.sleep', new_callable=AsyncMock), \
             patch('app.services.forum_scheduler.ForumScheduler._broadcast_system_message', new_callable=AsyncMock), \
             patch('app.services.forum_scheduler.ForumScheduler._broadcast_system_log', new_callable=AsyncMock) as mock_broadcast_log, \
             patch('app.services.forum_scheduler.ForumScheduler._moderator_speak', new_callable=AsyncMock), \
             patch.object(scheduler, '_is_forum_running', return_value=True), \
             patch('app.services.forum_scheduler.ParticipantAgent', return_value=mock_agent), \
             patch('app.services.forum_scheduler.ModeratorAgent'), \
             patch('app.services.forum_scheduler.SharedMemory'):
             
             # Run loop
             # We set get_forum side_effect to return None eventually to break the loop
             
             await scheduler._run_forum_loop(forum_id)
             
             # Verify that _agent_speak was called (implied by the flow reaching speak)
             # But _agent_speak is internal method. We didn't patch it, so it runs.
             # It calls agent.speak (mocked to fail).
             # Then it should call _broadcast_system_log with error.
             
             # Check calls to broadcast_log
             # We expect: 
             # 1. Start loop
             # 2. Moderator ready
             # 3. Opening
             # 4. Thinking...
             # 5. Error log for agent speak
             
             error_logs = [call for call in mock_broadcast_log.call_args_list if "发言生成失败" in str(call)]
             self.assertTrue(len(error_logs) > 0, "Should have broadcasted the API error")
             print("Found error logs:", error_logs)

if __name__ == '__main__':
    unittest.main()
