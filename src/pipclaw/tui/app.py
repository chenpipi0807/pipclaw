"""PipClaw 主 TUI 应用，对应 claw-code main.rs LiveCli。"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label

from ..api.client import PipClawClient
from ..api.types import TokenUsage
from ..commands.slash import handle_slash_command, is_slash_command
from ..runtime.conversation import ConversationRuntime
from ..runtime.permissions import PermissionMode, PermissionPolicy
from ..runtime.session import Session
from ..tools.executor import make_executor
from ..tools.specs import get_tool_specs
from .chat_panel import ChatPanel, UserSubmit
from .status_bar import StatusBar

SYSTEM_PROMPT = """你是 PipClaw，一个强大的 AI 编程助手。
你运行在用户的本地终端中，拥有读写文件、执行命令等工具能力。

当前工作目录已在上下文中提供。请遵循以下原则：
- 优先理解用户意图，再决定是否使用工具
- 修改文件前先用 read_file 阅读现有内容
- bash 命令尽量精准，避免高风险操作
- 用中文回复，代码块使用对应语言标注
"""


class PipClawApp(App):
    """主应用。"""

    CSS_PATH = "styles.tcss"
    TITLE = "PipClaw"
    BINDINGS = [
        ("ctrl+q", "quit", "退出"),
        ("tab", "focus_next", "切换焦点"),
        ("ctrl+l", "clear_chat", "清空对话"),
    ]

    def __init__(self, project_root: Path, project_name: str, session_id: str | None = None) -> None:
        super().__init__()
        self.project_root = project_root
        self.project_name = project_name
        self._session_id = session_id or f"session-{int(time.time())}"

        # 初始化 agent 运行时
        self._client = PipClawClient()
        self._executor = make_executor(project_root)
        self._permission = PermissionPolicy(mode=PermissionMode.DANGER_FULL_ACCESS)
        self._runtime = ConversationRuntime(
            client=self._client,
            tool_executor=self._executor,
            tool_specs=get_tool_specs(),
            permission_policy=self._permission,
            system_prompt=SYSTEM_PROMPT + f"\n当前项目根目录：{project_root}",
        )

        self._busy = False
        self._switch_to_new_project = False

        # 写入当前项目路径供 yazi 联动
        _state_dir = Path.home() / ".pipclaw"
        _state_dir.mkdir(exist_ok=True)
        (_state_dir / "current-project.txt").write_text(str(project_root), encoding="utf-8")

    # ── 布局 ──────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Label(
            f"[bold #58a6ff]PipClaw[/bold #58a6ff]  "
            f"[#8b949e]项目：{self.project_name}  [{self.project_root}][/#8b949e]",
            id="title-bar",
        )
        with Horizontal(id="main-container"):
            yield ChatPanel(id="chat-panel")
        yield StatusBar(
            model="kimi-k2.5",
            project=self.project_name,
            session_id=self._session_id,
            id="status-bar",
        )

    def on_mount(self) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        chat.append_user.__doc__  # 触发 mount 后的焦点设置（已在 ChatPanel.on_mount 处理）
        self._load_welcome()

    def _load_welcome(self) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        chat.start_assistant_turn()
        chat.append_text_delta(
            f"你好！我是 PipClaw，当前项目：{self.project_name}\n"
            f"工作目录：{self.project_root}\n\n"
            "可用斜杠命令：/help /clear /status /cost /permissions\n"
            "退出：Ctrl+Q   清空对话：Ctrl+L"
        )
        chat.end_assistant_turn()

    # ── 用户提交消息 ──────────────────────────────────────────────────────────

    async def on_user_submit(self, event: UserSubmit) -> None:
        if self._busy:
            return
        self._busy = True

        text = event.text.strip()
        chat = self.query_one("#chat-panel", ChatPanel)

        # 斜杠命令
        if is_slash_command(text):
            response = handle_slash_command(text, self._runtime, self)
            chat.append_user(text)
            chat.start_assistant_turn()
            chat.append_text_delta(response)
            chat.end_assistant_turn()
            self._busy = False
            return

        chat.append_user(text)
        chat.set_thinking(True)

        # 在工作线程执行 agent loop（避免阻塞 TUI 事件循环）
        await asyncio.get_event_loop().run_in_executor(None, self._run_agent_turn, text)
        self._busy = False

    def _run_agent_turn(self, user_input: str) -> None:
        """在线程池中运行 agent loop，通过 call_from_thread 更新 UI。"""
        chat = self.query_one("#chat-panel", ChatPanel)
        status = self.query_one("#status-bar", StatusBar)

        first_text = True

        def on_text_delta(delta: str) -> None:
            nonlocal first_text
            if first_text:
                self.call_from_thread(chat.set_thinking, False)
                self.call_from_thread(chat.start_assistant_turn)
                first_text = False
            self.call_from_thread(chat.append_text_delta, delta)

        def on_tool_call(tool_name: str, input_json: str) -> None:
            self.call_from_thread(chat.set_thinking, False)
            self.call_from_thread(chat.append_tool_call, tool_name, input_json)

        def on_tool_result(tool_name: str, output: str, is_error: bool) -> None:
            self.call_from_thread(chat.append_tool_result, tool_name, output, is_error)

        try:
            summary = self._runtime.run_turn(
                user_input,
                on_text_delta=on_text_delta,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
            )
            self.call_from_thread(chat.end_assistant_turn)
            self.call_from_thread(status.update_usage, summary.usage)
        except Exception as e:
            self.call_from_thread(chat.set_thinking, False)
            self.call_from_thread(chat.append_error, str(e))

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_clear_chat(self) -> None:
        self._runtime.clear_session()
        chat = self.query_one("#chat-panel", ChatPanel)
        chat.query_one("#chat-history").clear()  # type: ignore[union-attr]
        self._session_id = f"session-{int(time.time())}"
        self.query_one("#status-bar", StatusBar).update_session(self._session_id)

    def switch_project(self) -> None:
        """退出当前 TUI，回到 main.py 的项目选择循环。"""
        self._switch_to_new_project = True
        self.exit()
