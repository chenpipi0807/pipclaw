"""Kimi API 客户端，对应 claw-code api/client.rs。

Kimi K2.5 与 OpenAI 格式完全兼容，直接用 openai SDK 切换 base_url。
Agent 工具调用场景关闭 thinking，避免 reasoning_content 上下文问题。
"""
from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any

from openai import OpenAI

from .types import (
    ApiRequest,
    AssistantEvent,
    MessageStopEvent,
    TextDeltaEvent,
    TokenUsage,
    ToolUseEvent,
    UsageEvent,
)

KIMI_BASE_URL = "https://api.moonshot.cn/v1"
DEFAULT_MODEL = "kimi-k2.5"
DEFAULT_MAX_TOKENS = 32768


class PipClawClient:
    """流式调用 Kimi K2.5，产出 AssistantEvent 序列。"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        thinking: bool = False,
    ) -> None:
        self.model = model
        self.thinking = thinking
        self._client = OpenAI(
            api_key=api_key or os.environ["MOONSHOT_API_KEY"],
            base_url=KIMI_BASE_URL,
        )

    def stream(
        self,
        request: ApiRequest,
        tools: list[dict] | None = None,
    ) -> Iterator[AssistantEvent]:
        """向 Kimi API 发起流式请求，yield AssistantEvent。"""
        messages = self._build_messages(request)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "extra_body": {
                "thinking": {"type": "enabled" if self.thinking else "disabled"}
            },
        }

        if tools:
            kwargs["tools"] = tools
            # thinking 模式下 tool_choice 只能 "auto" 或 "none"
            kwargs["tool_choice"] = "auto"

        stream = self._client.chat.completions.create(**kwargs)

        # 收集各工具调用的参数片段（按 index 归并）
        tool_accum: dict[int, dict[str, Any]] = {}
        usage_data: dict[str, int] = {}

        for chunk in stream:
            # usage 信息
            if hasattr(chunk, "usage") and chunk.usage:
                usage_data = {
                    "input_tokens": chunk.usage.prompt_tokens or 0,
                    "output_tokens": chunk.usage.completion_tokens or 0,
                }

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason

            # 文本片段
            if delta.content:
                yield TextDeltaEvent(text=delta.content)

            # 工具调用片段（流式下参数是分块到达的）
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_accum:
                        tool_accum[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name or "",
                            "args": "",
                        }
                    if tc.id:
                        tool_accum[idx]["id"] = tc.id
                    if tc.function.name:
                        tool_accum[idx]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_accum[idx]["args"] += tc.function.arguments

            # 流结束
            if finish_reason in ("stop", "tool_calls", "length"):
                break

        # 发出完整的工具调用事件
        for tc_data in sorted(tool_accum.values(), key=lambda x: list(tool_accum.values()).index(x)):
            yield ToolUseEvent(
                id=tc_data["id"],
                name=tc_data["name"],
                input=tc_data["args"],
            )

        if usage_data:
            yield UsageEvent(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
            )

        yield MessageStopEvent()

    def _build_messages(self, request: ApiRequest) -> list[dict]:
        messages: list[dict] = []

        if request.system:
            messages.append({"role": "system", "content": request.system})

        for msg in request.messages:
            m: dict[str, Any] = {"role": msg.role}

            if msg.tool_call_id:
                # tool result：content 可以是 str 或 list（多模态）
                m["tool_call_id"] = msg.tool_call_id
                m["content"] = msg.content  # list[dict] 直接透传给 Kimi API
            elif msg.tool_calls:
                # assistant with tool_calls
                m["content"] = msg.content or ""
                m["tool_calls"] = msg.tool_calls
                if msg.reasoning_content and self.thinking:
                    m["reasoning_content"] = msg.reasoning_content
            else:
                m["content"] = msg.content

            messages.append(m)

        return messages
