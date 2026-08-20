"""NPC 异步状态更新的离线单元测试。"""

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch


batch_generator = types.ModuleType("batch_generator")
batch_generator.get_batch_generator = Mock()
sys.modules.setdefault("batch_generator", batch_generator)

module_path = Path(__file__).with_name("state_manager.py")
spec = importlib.util.spec_from_file_location("state_manager", module_path)
state_manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state_manager)


class NPCStateManagerTest(unittest.IsolatedAsyncioTestCase):
    async def test_update_runs_batch_generation_in_worker_thread(self):
        manager = object.__new__(state_manager.NPCStateManager)
        manager.batch_generator = Mock()
        manager.current_dialogues = {}
        manager.last_update = None
        manager.next_update_time = None
        manager._update_lock = asyncio.Lock()
        dialogues = {"张三": "今天天气不错。"}

        with patch.object(
            asyncio,
            "to_thread",
            new=AsyncMock(return_value=dialogues),
        ) as to_thread:
            await manager._update_npc_states()

        to_thread.assert_awaited_once_with(
            manager.batch_generator.generate_batch_dialogues
        )
        manager.batch_generator.generate_batch_dialogues.assert_not_called()
        self.assertEqual(manager.current_dialogues, dialogues)

    async def test_concurrent_updates_are_serialized(self):
        manager = object.__new__(state_manager.NPCStateManager)
        manager.batch_generator = Mock()
        manager.current_dialogues = {}
        manager.last_update = None
        manager.next_update_time = None
        manager._update_lock = asyncio.Lock()
        active_calls = 0
        max_active_calls = 0

        async def fake_to_thread(function):
            nonlocal active_calls, max_active_calls
            self.assertIs(function, manager.batch_generator.generate_batch_dialogues)
            active_calls += 1
            max_active_calls = max(max_active_calls, active_calls)
            await asyncio.sleep(0)
            active_calls -= 1
            return {"张三": "更新完成。"}

        with patch.object(asyncio, "to_thread", side_effect=fake_to_thread):
            await asyncio.gather(
                manager._update_npc_states(),
                manager._update_npc_states(),
            )

        self.assertEqual(max_active_calls, 1)


if __name__ == "__main__":
    unittest.main()
