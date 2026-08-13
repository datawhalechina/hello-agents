from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.forum_scheduler import restore_framework_history


def test_participant_history_restores_self_messages_as_assistant():
    agent = MagicMock()
    messages = [
        SimpleNamespace(speaker_name="Ada", content="My point"),
        SimpleNamespace(speaker_name="Turing", content="A reply"),
    ]

    restore_framework_history(agent, messages, self_name="Ada")

    restored = [call.args[0] for call in agent.add_message.call_args_list]
    assert [(message.role, message.content) for message in restored] == [
        ("assistant", "[Ada] My point"),
        ("user", "[Turing] A reply"),
    ]


def test_moderator_history_restores_transcript_as_user_context():
    moderator = MagicMock()

    restore_framework_history(
        moderator,
        [SimpleNamespace(speaker_name="Ada", content="Previous discussion")],
    )

    message = moderator.add_message.call_args.args[0]
    assert message.role == "user"
    assert message.content == "[Ada] Previous discussion"
