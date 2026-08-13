import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.forum_scheduler import ForumScheduler
from app.agent.agent import ParticipantAgent

class TestForumScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = ForumScheduler()
        # Mock manager
        self.patcher = patch('app.services.forum_scheduler.manager')
        self.mock_manager = self.patcher.start()
        self.mock_manager.broadcast = AsyncMock()
        
    def tearDown(self):
        self.patcher.stop()

    def test_agent_speak_broadcasts_chunks(self):
        # Setup
        mock_db = MagicMock()
        forum_id = 1
        agent = ParticipantAgent("Test Agent", {"system_prompt": "test"}, 1, "test")
        thought = {"action": "speak"}
        context = "test context"
        
        # Mock speak to return a generator of chunks
        def mock_speak(*args):
            return iter("Hello World")
            
        agent.speak = mock_speak
        
        # Mock participants query
        mock_p = MagicMock()
        mock_p.persona.name = "Test Agent"
        mock_p.persona_id = 123
        
        with patch('app.services.forum_scheduler.get_forum_participants', return_value=[mock_p]), \
             patch('app.services.forum_scheduler.create_message') as mock_create_msg, \
             patch.object(self.scheduler, '_is_forum_running', return_value=True):
            mock_create_msg.return_value.id = 1

            # Run
            import asyncio
            asyncio.run(self.scheduler._agent_speak(forum_id, agent, thought, context))
            
            # Verify broadcasts
            # We expect len("Hello World") calls to broadcast_chunk
            # And 1 call to broadcast_message
            
            # Check broadcast_chunk calls (via manager.broadcast)
            # manager.broadcast is called for chunks AND final message
            
            calls = self.mock_manager.broadcast.call_args_list
            
            # Filter for chunks
            chunk_calls = [c for c in calls if c[0][1]['type'] == 'message_chunk']
            self.assertEqual(len(chunk_calls), len("Hello World"))
            
            # Check content of first chunk
            self.assertEqual(chunk_calls[0][0][1]['data']['content'], 'H')
            self.assertEqual(chunk_calls[0][0][1]['data']['speaker_name'], "Test Agent")
            self.assertEqual(chunk_calls[0][0][1]['data']['persona_id'], 123)
            
            # Filter for final message
            final_calls = [c for c in calls if c[0][1]['type'] == 'new_message']
            self.assertEqual(len(final_calls), 1)
            self.assertEqual(final_calls[0][0][1]['data']['content'], "Hello World")

if __name__ == '__main__':
    unittest.main()
