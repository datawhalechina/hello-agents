from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.forum_scheduler import ForumScheduler, forum_deadline_epoch, to_epoch_seconds


@pytest.mark.parametrize(
    ("persisted_value", "expected"),
    [
        (datetime(2026, 8, 12, 12, 0, 0, tzinfo=timezone.utc), 1786536000.0),
        ("2026-08-12T12:00:00+00:00", 1786536000.0),
        (1786536000, 1786536000.0),
        (1786536000000, 1786536000.0),
    ],
)
def test_recovery_clock_normalizes_datetime_representations(persisted_value, expected):
    assert to_epoch_seconds(persisted_value) == expected


def test_thirty_minute_deadline_is_exactly_1800_seconds():
    start = datetime(2026, 8, 13, 8, 0, 0, tzinfo=timezone.utc)
    assert forum_deadline_epoch(start, 30) - to_epoch_seconds(start) == 1800


@pytest.mark.asyncio
async def test_recover_running_forums_restarts_persisted_tasks():
    scheduler = ForumScheduler()
    result = MagicMock()
    result.rows = [(3,), (7,)]
    result.columns = ["id"]
    db = MagicMock()
    db.execute.return_value = result

    with patch.object(scheduler, "_get_db") as get_db, patch.object(
        scheduler, "start_forum", new_callable=AsyncMock
    ) as start_forum:
        get_db.return_value.__enter__.return_value = db
        recovered = await scheduler.recover_running_forums()

    assert recovered == [3, 7]
    assert [call.args[0] for call in start_forum.await_args_list] == [3, 7]
    assert all(call.kwargs == {"recovering": True} for call in start_forum.await_args_list)


@pytest.mark.asyncio
async def test_recovered_forum_skips_opening_and_uses_persisted_clock():
    scheduler = ForumScheduler()
    forum = MagicMock(
        id=3,
        status="running",
        duration_minutes=30,
        start_time="2026-08-12 12:00:00",
        moderator=None,
        summary_history=[],
        ablation_flags='{"mock_llm": true}',
    )

    with patch.object(scheduler, "_get_db") as get_db, patch(
        "app.services.forum_scheduler.get_forum",
        side_effect=[forum, forum],
    ), patch(
        "app.services.forum_scheduler.get_forum_participants", return_value=[]
    ), patch(
        "app.services.forum_scheduler.get_forum_messages", return_value=[]
    ), patch(
        "app.services.forum_scheduler.update_forum"
    ) as update_forum, patch.object(
        scheduler, "_broadcast_system_message", new_callable=AsyncMock
    ) as broadcast_system_message, patch.object(
        scheduler, "_broadcast_system_log", new_callable=AsyncMock
    ), patch.object(
     scheduler, "_moderator_speak", new_callable=AsyncMock
     ) as moderator_speak, patch.object(
         scheduler, "_flush_logs_to_db", new_callable=AsyncMock
     ), patch(
         "app.services.forum_scheduler.restore_framework_history"
     ), patch(
         "app.services.forum_scheduler.ModeratorAgent"
     ), patch(
         "app.services.forum_scheduler.time.time",
        return_value=datetime.fromisoformat("2026-08-12 12:30:00").timestamp(),
    ), patch(
        "app.services.forum_scheduler.manager.broadcast", new_callable=AsyncMock
    ):
        get_db.return_value.__enter__.return_value = MagicMock()
        await scheduler._run_forum_loop(3, recovering=True)

    broadcast_system_message.assert_not_awaited()
    assert not any(call.args[2] == "opening" for call in moderator_speak.await_args_list)
    assert any(call.args[2] == "closing" for call in moderator_speak.await_args_list)
    assert not any(call.kwargs.get("start_time") for call in update_forum.call_args_list)
    assert any(call.kwargs.get("ablation_flags", {}).get("mock_llm") for call in moderator_speak.call_args_list)


def test_start_persists_controlled_flags_before_scheduling():
    from app.services.forum_service import ForumService

    db = MagicMock()
    forum = MagicMock(creator_id=1, status="pending", start_time=None, duration_minutes=30)
    service = ForumService(db)

    with patch("app.services.forum_service.get_forum", return_value=forum), patch(
        "app.services.forum_service.update_forum"
    ) as update_forum, patch(
        "app.services.forum_service.scheduler.start_forum", new_callable=AsyncMock
    ) as start_forum:
        result = __import__("asyncio").run(
            service.start_forum(9, user_id=1, ablation_flags={"mock_llm": True})
        )

    assert result["status"] == "started"
    update_forum.assert_called_once()
    assert update_forum.call_args.args == (db, 9)
    assert update_forum.call_args.kwargs["status"] == "running"
    assert update_forum.call_args.kwargs["ablation_flags"] == {"mock_llm": True}
    assert isinstance(update_forum.call_args.kwargs["start_time"], datetime)
    assert update_forum.call_args.kwargs["start_time"].tzinfo is timezone.utc
    assert result["duration_minutes"] == 30
    assert result["start_time"] == update_forum.call_args.kwargs["start_time"]
    start_forum.assert_awaited_once_with(9, {"mock_llm": True})


@pytest.mark.asyncio
async def test_shutdown_preserves_database_state():
    scheduler = ForumScheduler()

    async def wait_forever():
        await __import__("asyncio").Event().wait()

    task = __import__("asyncio").create_task(wait_forever())
    scheduler.running_tasks[1] = task
    with patch("app.services.forum_scheduler.update_forum") as update_forum:
        await scheduler.shutdown()

    assert task.cancelled()
    update_forum.assert_not_called()
