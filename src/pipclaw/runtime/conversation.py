"""Agent 对话循环，对应 claw-code runtime/conversation.rs。

核心逻辑：
  用户输入 → API 调用 → 解析事件 → 执行工具 → 追加结果 → 循环直到无工具调用
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Iterator

from ..api.client import PipClawClient
from ..api.types import (
    ApiMessage,
    ApiRequest,
    MessageStopEvent,
    TextDeltaEvent,
    TokenUsage,
    ToolUseEvent,
    UsageEvent,
)
from .permissions import PermissionPolicy
from .session import (
    ContentBlock,
    ConversationMessage,
    Session,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

MAX_ITERATIONS = 50
AUTO_COMPACT_INPUT_THRESHOLD = 200_000

# 工具执行函数类型：(tool_name, input_json) -> output_str
ToolExecutorFn = Callable[[str, str], str]

# 流式文本回调（每个 delta 调用一次，用于 TUI 实时渲染）
StreamCallback = Callable[[str], None]

# 工具调用通知回调
ToolCallCallback = Callable[[str, str], None]    # (tool_name, input_json)
ToolResultCallback = Callable[[str, str, bool], None]  # (tool_name, output, is_error)


@dataclass
class TurnSummary:
    text: str
    tool_calls: int = 0
    usage: TokenUsage = field(default_factory=TokenUsage)
    iterations: int = 0
    error: str | None = None


class ConversationRuntime:
    """驱动完整 agent 循环。"""

    def __init__(
        self,
        client: PipClawClient,
        tool_executor: ToolExecutorFn,
        tool_specs: list[dict],
        permission_policy: PermissionPolicy,
        system_prompt: str = "",
        session: Session | None = None,
    ) -> None:
        self.client = client
        self.tool_executor = tool_executor
        self.tool_specs = tool_specs
        self.permission_policy = permission_policy
        self.system_prompt = system_prompt
        self.session = session or Session()
        self._cumulative_usage = TokenUsage()

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    def run_turn(
        self,
        user_input: str,
        on_text_delta: StreamCallback | None = None,
        on_tool_call: ToolCallCallback | None = None,
        on_tool_result: ToolResultCallback | None = None,
    ) -> TurnSummary:
        """执行一轮对话（可能包含多次工具调用）。"""
        self.session.messages.append(ConversationMessage.user_text(user_input))

        full_text = ""
        total_tool_calls = 0
        turn_usage = TokenUsage()
        iterations = 0

        for iterations in range(1, MAX_ITERATIONS + 1):
            request = self._build_request()
            events = list(self.client.stream(request, tools=self.tool_specs or None))

            # 解析事件流 → 构建 assistant message
            text_buf = ""
            tool_uses: list[ToolUseBlock] = []
            usage: TokenUsage | None = None

            for event in events:
                if isinstance(event, TextDeltaEvent):
                    text_buf += event.text
                    if on_text_delta:
                        on_text_delta(event.text)
                elif isinstance(event, ToolUseEvent):
                    tool_uses.append(ToolUseBlock(id=event.id, name=event.name, input=event.input))
                elif isinstance(event, UsageEvent):
                    usage = TokenUsage(
                        input_tokens=event.input_tokens,
                        output_tokens=event.output_tokens,
                    )
                    turn_usage = turn_usage + usage
                    self._cumulative_usage = self._cumulative_usage + usage

            # 构建 blocks
            blocks: list[ContentBlock] = []
            if text_buf:
                blocks.append(TextBlock(text=text_buf))
                full_text += text_buf
            for tu in tool_uses:
                blocks.append(tu)

            if not blocks:
                break

            self.session.messages.append(ConversationMessage.assistant(blocks, usage))

            if not tool_uses:
                break

            # 执行所有工具调用
            for tu in tool_uses:
                total_tool_calls += 1
                if on_tool_call:
                    on_tool_call(tu.name, tu.input)

                outcome = self.permission_policy.authorize(tu.name, tu.input)
                if not outcome.allowed:
                    output = outcome.reason
                    is_error = True
                else:
                    try:
                        output = self.tool_executor(tu.name, tu.input)
                        is_error = False
                    except Exception as e:
                        output = str(e)
                        is_error = True

                # 多模态结果转为可读摘要用于 TUI 显示
                display = output if isinstance(output, str) else f"[多模态内容 {len(output)} 块]"
                if on_tool_result:
                    on_tool_result(tu.name, display, is_error)

                self.session.messages.append(
                    ConversationMessage.tool_result(tu.id, tu.name, output, is_error)
                )

        return TurnSummary(
            text=full_text,
            tool_calls=total_tool_calls,
            usage=turn_usage,
            iterations=iterations,
        )

    @property
    def cumulative_usage(self) -> TokenUsage:
        return self._cumulative_usage

    def clear_session(self) -> None:
        self.session = Session()
        self._cumulative_usage = TokenUsage()

    # ── 内部 ──────────────────────────────────────────────────────────────────

    def _build_request(self) -> ApiRequest:
        api_messages: list[ApiMessage] = []

        for msg in self.session.messages:
            if msg.role == "user":
                text = next((b.text for b in msg.blocks if isinstance(b, TextBlock)), "")
                api_messages.append(ApiMessage(role="user", content=text))

            elif msg.role == "assistant":
                text_parts = [b.text for b in msg.blocks if isinstance(b, TextBlock)]
                tool_uses = [b for b in msg.blocks if isinstance(b, ToolUseBlock)]

                content = "".join(text_parts)
                tool_calls = None

                if tool_uses:
                    tool_calls = [
                        {
                            "id": tu.id,
                            "type": "function",
                            "function": {"name": tu.name, "arguments": tu.input},
                        }
                        for tu in tool_uses
                    ]

                api_messages.append(ApiMessage(
                    role="assistant",
                    content=content,
                    tool_calls=tool_calls,
                ))

            elif msg.role == "tool":
                for b in msg.blocks:
                    if isinstance(b, ToolResultBlock):
                        api_messages.append(ApiMessage(
                            role="tool",
                            content=b.output,
                            tool_call_id=b.tool_use_id,
                        ))

        return ApiRequest(messages=api_messages, system=self.system_prompt)
