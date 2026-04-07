"""API 层类型定义，对应 claw-code api/types.rs"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ApiMessage:
    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict]
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None
    # thinking 模式下模型返回的推理内容，多步工具调用时需要保留
    reasoning_content: str | None = None


@dataclass
class ApiRequest:
    messages: list[ApiMessage]
    system: str = ""


# ── AssistantEvent（流式事件） ──────────────────────────────────────────────

@dataclass
class TextDeltaEvent:
    text: str


@dataclass
class ToolUseEvent:
    id: str
    name: str
    input: str          # JSON string


@dataclass
class UsageEvent:
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class MessageStopEvent:
    pass


AssistantEvent = TextDeltaEvent | ToolUseEvent | UsageEvent | MessageStopEvent


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_input_tokens=self.cache_creation_input_tokens + other.cache_creation_input_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens + other.cache_read_input_tokens,
        )
