import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import json
from app.services.forum_scheduler import ForumScheduler
from app.agent.agent import ModeratorAgent

class TestStreamRobustness(unittest.IsolatedAsyncioTestCase):
    async def test_moderator_stream_fields(self):
        """
        Verify that moderator streaming broadcasts include stream_id and moderator_id.
        """
        scheduler = ForumScheduler()
        
        # Mock DB and objects
        mock_db = MagicMock()
        mock_forum = MagicMock()
        mock_forum.id = 1
        mock_forum.moderator_id = 99
        mock_forum.summary_history = []
        
        # Mock get_forum to return our mock forum
        # We need to patch 'app.services.forum_scheduler.get_forum'
        
        # Mock ModeratorAgent to return a generator
        mock_moderator = MagicMock(spec=ModeratorAgent)
        mock_moderator.name = "TestHost"
        
        def mock_opening(guests):
            yield "Hello"
            yield " World"
            
        # Patch dependencies
        with patch('app.services.forum_scheduler.get_forum', return_value=mock_forum), \
             patch('app.services.forum_scheduler.create_message') as mock_create_msg, \
             patch('app.services.forum_scheduler.update_forum'), \
             patch('app.services.forum_scheduler.manager') as mock_manager, \
             patch.object(scheduler, '_is_forum_running', return_value=True), \
             patch('asyncio.to_thread', side_effect=lambda func, *args: func(*args)) as mock_to_thread:
            
            # Make broadcast awaitable
            mock_manager.broadcast = AsyncMock()
            
            # Setup moderator mock methods
            mock_moderator.opening = mock_opening
            
            # Run _moderator_speak
            # We assume asyncio.to_thread executes the function immediately for this test
            mock_create_msg.return_value.id = 1
            await scheduler._moderator_speak(1, mock_moderator, "opening", guests=[])
            
            # Verify broadcasts
            calls = mock_manager.broadcast.call_args_list
            chunk_calls = [call for call in calls if call[0][1]['type'] == 'message_chunk']
            message_calls = [call for call in calls if call[0][1]['type'] == 'new_message']
            speech_logs = [
                call for call in calls
                if call[0][1]['type'] == 'system_log'
                and call[0][1]['data']['level'] == 'speech'
            ]
            self.assertEqual(len(chunk_calls), 2)
            self.assertEqual(len(message_calls), 1)
            self.assertGreaterEqual(len(speech_logs), 1)

            # Check that stream_id and moderator_id are present in chunks
            # First call: Chunk 1
            call_args_1 = chunk_calls[0]
            payload_1 = call_args_1[0][1]
            self.assertEqual(payload_1['type'], 'message_chunk')
            self.assertIn('stream_id', payload_1['data'])
            self.assertEqual(payload_1['data']['moderator_id'], 99)

            call_args_msg = message_calls[0]
            payload_msg = call_args_msg[0][1]
            self.assertEqual(payload_msg['type'], 'new_message')
            self.assertIn('stream_id', payload_msg['data'])
            self.assertEqual(payload_msg['data']['moderator_id'], 99)

if __name__ == '__main__':
    unittest.main()
