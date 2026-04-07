"""底部状态栏：模型名、token 计数、会话 ID。"""
from __future__ import annotations

from textual.widget import Widget
from textual.widgets import Label

from ..api.types import TokenUsage


class StatusBar(Widget):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: #161b22;
        layout: horizontal;
    }
    StatusBar Label {
        color: #8b949e;
        padding: 0 1;
    }
    StatusBar .sep {
        color: #30363d;
    }
    """

    def __init__(self, model: str, project: str, session_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model = model
        self._project = project
        self._session_id = session_id
        self._usage = TokenUsage()

    def compose(self):
        yield Label(f"模型: {self._model}", id="sb-model")
        yield Label("│", classes="sep")
        yield Label(f"项目: {self._project}", id="sb-project")
        yield Label("│", classes="sep")
        yield Label("tokens: 0", id="sb-tokens")
        yield Label("│", classes="sep")
        yield Label(f"会话: {self._session_id}", id="sb-session")

    def update_usage(self, usage: TokenUsage) -> None:
        self._usage = self._usage + usage
        self.query_one("#sb-tokens", Label).update(
            f"tokens: {self._usage.total_tokens:,}  (in:{self._usage.input_tokens:,} out:{self._usage.output_tokens:,})"
        )

    def update_session(self, session_id: str) -> None:
        self._session_id = session_id
        self.query_one("#sb-session", Label).update(f"会话: {session_id}")
