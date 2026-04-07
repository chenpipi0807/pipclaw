"""Session 序列化/反序列化测试。"""
import json
import tempfile
from pathlib import Path

from kimi_agent.runtime.session import (
    ConversationMessage,
    Session,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)


def test_session_roundtrip(tmp_path):
    session = Session()
    session.messages.append(ConversationMessage.user_text("hello"))
    session.messages.append(ConversationMessage.assistant(
        blocks=[TextBlock(text="world"), ToolUseBlock(id="t1", name="bash", input='{"command":"ls"}')],
    ))
    session.messages.append(ConversationMessage.tool_result("t1", "bash", "file.txt", False))

    path = tmp_path / "session.json"
    session.save(path)
    loaded = Session.load(path)

    assert len(loaded.messages) == 3
    assert loaded.messages[0].role == "user"
    assert isinstance(loaded.messages[1].blocks[0], TextBlock)
    assert isinstance(loaded.messages[1].blocks[1], ToolUseBlock)
    assert isinstance(loaded.messages[2].blocks[0], ToolResultBlock)
    assert loaded.messages[2].blocks[0].is_error is False
