"""左侧对话面板：消息历史 + 流式输出 + 输入框。"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import RichLog, TextArea


class UserSubmit(Message):
    """用户提交消息事件。"""
    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class ChatInput(TextArea):
    """多行输入框，Enter 提交，Shift+Enter 换行。"""

    def on_key(self, event) -> None:
        # 只处理纯 Enter（非 IME 组合状态下）
        if event.key == "enter":
            event.prevent_default()   # 不插入换行，但不 stop()，允许 IME 事件继续
            text = self.text.strip()
            if text:
                self.clear()
                self.post_message(UserSubmit(text))
        elif event.key == "shift+enter":
            event.prevent_default()
            self.insert("\n")


class ChatPanel(Widget):
    """左侧完整对话区域。"""

    is_thinking: reactive[bool] = reactive(False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # 流式文本行缓冲：积累到换行符才写出一行
        self._stream_buf: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="chat-container"):
            yield RichLog(id="chat-history", highlight=True, markup=True, wrap=True)
            with Vertical(id="chat-input-area"):
                yield ChatInput(id="chat-input")

    def on_mount(self) -> None:
        self.query_one("#chat-input").focus()

    # ── 公开方法（由 App 调用） ────────────────────────────────────────────────

    # ── 内部辅助：用 Rich Text 对象写出，完全绕开 markup 解析 ──────────────────

    def _write(self, text: str, style: str = "") -> None:
        from rich.text import Text
        log = self.query_one("#chat-history", RichLog)
        log.write(Text(text, style=style))

    # ── 公开方法（由 App 调用） ────────────────────────────────────────────────

    def append_user(self, text: str) -> None:
        self._write("You", style="bold #58a6ff")
        for line in text.splitlines():
            self._write(line, style="#c9d1d9")
        self._write("")

    def start_assistant_turn(self) -> None:
        self._stream_buf = ""
        self._write("Kimi", style="bold #3fb950")

    def append_text_delta(self, delta: str) -> None:
        """行缓冲流式输出：遇到换行才写出一行。"""
        self._stream_buf += delta
        lines = self._stream_buf.split("\n")
        for line in lines[:-1]:
            self._write(line, style="#c9d1d9")
        self._stream_buf = lines[-1]

    def end_assistant_turn(self) -> None:
        """冲刷剩余缓冲，结束本轮输出。"""
        if self._stream_buf:
            self._write(self._stream_buf, style="#c9d1d9")
            self._stream_buf = ""
        self._write("")

    def append_tool_call(self, tool_name: str, input_json: str) -> None:
        bar = "─" * (len(tool_name) + 12)
        self._write(f"╭─ 工具调用: {tool_name} ─╮", style="bold #d29922")
        preview = input_json[:200] + ("…" if len(input_json) > 200 else "")
        self._write(preview, style="#8b949e")
        self._write(f"╰{bar}╯", style="bold #d29922")

    def append_tool_result(self, tool_name: str, output: str, is_error: bool) -> None:
        icon = "✗" if is_error else "✓"
        color = "#f85149" if is_error else "#3fb950"
        preview = output[:300] + ("…" if len(output) > 300 else "")
        self._write(f"{icon} {tool_name}  {preview}", style=color)

    def append_error(self, msg: str) -> None:
        self._write(f"错误  {msg}", style="bold #f85149")
        self._write("")

    def set_thinking(self, thinking: bool) -> None:
        self.is_thinking = thinking
        if thinking:
            self._write("思考中…", style="italic #6e7681")
