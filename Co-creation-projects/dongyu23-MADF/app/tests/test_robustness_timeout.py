import asyncio
import threading
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from app.services.forum_scheduler import ForumScheduler
from app.agent.agent import ParticipantAgent, ModeratorAgent

class TestRobustnessTimeout(unittest.IsolatedAsyncioTestCase):
    async def test_agent_speak_timeout_handling(self):
        """
        Test that _agent_speak handles LLM timeout (returning None) gracefully.
        """
        scheduler = ForumScheduler()
        mock_db = MagicMock()
        forum_id = 1
        
        # Mock agent
        agent = ParticipantAgent("Test Agent", {"system_prompt": "test"}, 1, "test")
        agent.persona_id = 123
        
        # Mock agent.speak to return None (simulating timeout/failure after retries)
        # The native HelloAgents stream can return no tokens.
        # Then agent.speak generator loop probably yields nothing or raises if not handled.
        # But here we mock agent.speak to return None directly (not a generator)
        # Our updated code checks `if gen:`.
        agent.speak = MagicMock(return_value=None)
        
        # Mock dependencies
        with patch('app.services.forum_scheduler.create_message') as mock_create_msg, \
             patch('app.services.forum_scheduler.get_forum_participants', return_value=[]), \
             patch('app.services.forum_scheduler.manager.broadcast', new_callable=AsyncMock) as mock_broadcast, \
             patch('app.services.forum_scheduler.ForumScheduler._broadcast_system_log', new_callable=AsyncMock) as mock_log, \
             patch.object(scheduler, '_is_forum_running', return_value=True), \
             patch('app.services.forum_scheduler.update_forum_participant') as mock_update_p:
            
            # Run _agent_speak
            # We must mock asyncio.to_thread because we mock agent.speak to be sync function
            # Or make agent.speak async if we don't mock to_thread?
            # It's easier to mock to_thread to return agent.speak()
            
            with patch('asyncio.to_thread', side_effect=lambda func, *args: func(*args)):
                await scheduler._agent_speak(forum_id, agent, {}, "context")
            
            # Verify:
            # It should handle None generator by logging warning and setting content to "(沉默)"
            # Then call create_message
            mock_create_msg.assert_called_once()
            args, kwargs = mock_create_msg.call_args
            # Args are (db, MessageCreate(...))
            # Check content inside MessageCreate
            msg_create = args[1]
            self.assertEqual(msg_create.content, "(沉默)")
            
    async def test_moderator_speak_timeout_handling(self):
        """
        Test that _moderator_speak handles LLM timeout gracefully.
        """
        scheduler = ForumScheduler()
        mock_db = MagicMock()
        forum_id = 1
        
        # Mock moderator
        mock_mod = MagicMock()
        mock_mod.name = "Moderator"
        
        # Mock opening to return None
        mock_mod.opening.return_value = None
        
        with patch('app.services.forum_scheduler.get_forum') as mock_get_forum, \
             patch('app.services.forum_scheduler.create_message') as mock_create_msg, \
             patch('app.services.forum_scheduler.manager.broadcast', new_callable=AsyncMock), \
             patch('app.services.forum_scheduler.ForumScheduler._broadcast_system_log', new_callable=AsyncMock), \
             patch('app.services.forum_scheduler.update_forum') as mock_update_f:
            
            mock_get_forum.return_value.moderator_id = 999
            
            with patch('asyncio.to_thread', side_effect=lambda func, *args: func(*args)):
                # Run
                await scheduler._moderator_speak(forum_id, mock_mod, "opening", [])
            
            # In our implementation for moderator:
            # if gen is None: logger.warning...
            # content remains ""
            # if content: create_message...
            # So create_message should NOT be called
            mock_create_msg.assert_not_called()

    async def test_agent_speak_exception_handling(self):
        """
        Test that _agent_speak handles generator exception gracefully.
        """
        scheduler = ForumScheduler()
        mock_db = MagicMock()
        forum_id = 1
        agent = ParticipantAgent("Test Agent", {"system_prompt": "test"}, 1, "test")
        agent.persona_id = 123
        
        # Mock generator that raises
        def faulty_generator(*args):
            yield "Hello"
            raise ValueError("Stream broken")
            
        agent.speak = MagicMock(return_value=faulty_generator())
        
        with patch('app.services.forum_scheduler.create_message') as mock_create_msg, \
             patch('app.services.forum_scheduler.get_forum_participants', return_value=[]), \
             patch('app.services.forum_scheduler.manager.broadcast', new_callable=AsyncMock), \
             patch('app.services.forum_scheduler.ForumScheduler._broadcast_system_log', new_callable=AsyncMock), \
             patch.object(scheduler, '_is_forum_running', return_value=True), \
             patch('app.services.forum_scheduler.update_forum_participant'), \
             patch('asyncio.to_thread', side_effect=lambda func, *args: func(*args)):
             
            await scheduler._agent_speak(forum_id, agent, {}, "context")
            
            # It should catch the exception inside the loop and proceed with partial content
            mock_create_msg.assert_called_once()
            msg_create = mock_create_msg.call_args[0][1]
            self.assertEqual(msg_create.content, "Hello")

    async def test_stopped_forum_discards_late_agent_output(self):
        scheduler = ForumScheduler()
        agent = ParticipantAgent("Test Agent", {"system_prompt": "test"}, 1, "test")
        agent.speak = MagicMock(return_value=iter(["late output"]))

        with patch('app.services.forum_scheduler.create_message') as mock_create_msg, \
             patch('app.services.forum_scheduler.get_forum_participants', return_value=[]), \
             patch.object(scheduler, '_is_forum_running', return_value=False), \
             patch('asyncio.to_thread', side_effect=lambda func, *args: func(*args)):
            await scheduler._agent_speak(1, agent, {}, "context")

        mock_create_msg.assert_not_called()

    async def test_running_only_log_is_dropped_after_stop(self):
        scheduler = ForumScheduler()

        with patch.object(scheduler, '_is_forum_running', return_value=False), \
             patch('app.services.forum_scheduler.manager.broadcast', new_callable=AsyncMock) as broadcast, \
             patch.object(scheduler, '_spawn_forum_task') as spawn_task:
            await scheduler._broadcast_system_log(
                1,
                "主持人正在构思",
                "thought",
                require_running=True,
            )

        broadcast.assert_not_awaited()
        spawn_task.assert_not_called()

    async def test_stop_waits_for_inflight_log_persistence(self):
        scheduler = ForumScheduler()
        persistence_started = threading.Event()
        allow_persistence_to_finish = threading.Event()
        persistence_finished = threading.Event()

        def push_message(*args, **kwargs):
            return False

        def create_system_log(*args, **kwargs):
            persistence_started.set()
            allow_persistence_to_finish.wait(timeout=5)
            persistence_finished.set()

        child = scheduler._spawn_forum_task(
            1,
            scheduler._persist_log_bg(
                1,
                "主持人正在构思",
                "thought",
                "System",
                "2026-08-12T12:00:00+08:00",
                require_running=True,
            ),
        )

        running_states = iter([True, False])

        with patch.object(scheduler, '_is_forum_running', side_effect=lambda forum_id: next(running_states)), \
             patch.object(scheduler, '_get_db') as get_db, \
             patch('app.services.forum_scheduler.get_forum', return_value=MagicMock(status='running')), \
             patch('app.services.forum_scheduler.update_forum'), \
             patch('app.services.forum_scheduler.manager.broadcast', new_callable=AsyncMock), \
             patch('app.core.cache.cache_service.push_message', side_effect=push_message), \
             patch('app.crud.crud_system_log.create_system_log', side_effect=create_system_log):
            get_db.return_value.__enter__.return_value = MagicMock()
            await asyncio.to_thread(persistence_started.wait, 5)

            stop_task = asyncio.create_task(scheduler.stop_forum(1))
            await asyncio.sleep(0.05)

            self.assertFalse(stop_task.done())
            self.assertFalse(persistence_finished.is_set())

            allow_persistence_to_finish.set()
            await asyncio.wait_for(stop_task, timeout=5)

        self.assertTrue(child.cancelled())
        self.assertTrue(persistence_finished.is_set())
        self.assertNotIn(1, scheduler.child_tasks)

    async def test_moderator_thinking_log_is_managed_and_running_only(self):
        scheduler = ForumScheduler()
        moderator = MagicMock(name="主持人")
        moderator.name = "主持人"
        moderator.opening.return_value = iter(())
        spawned = []

        def capture_task(forum_id, coroutine):
            spawned.append((forum_id, dict(coroutine.cr_frame.f_locals)))
            coroutine.close()
            return MagicMock()

        with patch.object(scheduler, '_get_db') as get_db, \
             patch('app.services.forum_scheduler.get_forum', return_value=MagicMock(moderator_id=2)), \
             patch.object(scheduler, '_spawn_forum_task', side_effect=capture_task), \
             patch('asyncio.to_thread', side_effect=lambda func, *args: func(*args)):
            get_db.return_value.__enter__.return_value = MagicMock()
            await scheduler._moderator_speak(1, moderator, "opening", guests=[])

        self.assertEqual(len(spawned), 1)
        self.assertEqual(spawned[0][0], 1)
        self.assertTrue(spawned[0][1]["require_running"])

    async def test_all_failed_thinks_close_forum_without_exposing_provider_error(self):
        scheduler = ForumScheduler()
        db = MagicMock()

        with patch.object(scheduler, '_get_db') as get_db, \
             patch('app.services.forum_scheduler.get_forum', return_value=MagicMock()), \
             patch('app.services.forum_scheduler.update_forum') as update_forum, \
             patch('app.services.forum_scheduler.manager.broadcast', new_callable=AsyncMock) as broadcast, \
             patch.object(scheduler, '_broadcast_system_log', new_callable=AsyncMock) as system_log:
            get_db.return_value.__enter__.return_value = db
            await scheduler._close_for_unavailable_agents(1)

        update_forum.assert_called_once_with(db, 1, status='closed')
        broadcast.assert_awaited_once_with(1, {'type': 'status_update', 'status': 'closed'})
        system_log.assert_awaited_once()
        assert '模型配置' in system_log.await_args.args[1]
        assert '401' not in system_log.await_args.args[1]

if __name__ == '__main__':
    unittest.main()
