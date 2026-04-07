"""会话数据结构，对应 claw-code runtime/session.rs。"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ..api.types import TokenUsage


# ── ContentBlock ──────────────────────────────────────────────────────────────

@dataclass
class TextBlock:
    text: str


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: str      # JSON string
    # tool_calls 格式（送给 API 用）
    raw_tool_calls: list[dict] | None = None


@dataclass
class ToolResultBlock:
    tool_use_id: str
    tool_name: str
    output: str | list   # str = 普通文本；list = 多模态内容块（video_url / image_url 等）
    is_error: bool = False


ContentBlock = TextBlock | ToolUseBlock | ToolResultBlock

MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass
class ConversationMessage:
    role: MessageRole
    blocks: list[ContentBlock]
    usage: TokenUsage | None = None

    # ── 工厂方法 ──────────────────────────────────────────────────────────────

    @classmethod
    def user_text(cls, text: str) -> ConversationMessage:
        return cls(role="user", blocks=[TextBlock(text=text)])

    @classmethod
    def assistant(cls, blocks: list[ContentBlock], usage: TokenUsage | None = None) -> ConversationMessage:
        return cls(role="assistant", blocks=blocks, usage=usage)

    @classmethod
    def tool_result(cls, tool_use_id: str, tool_name: str, output: str | list, is_error: bool = False) -> ConversationMessage:
        return cls(
            role="tool",
            blocks=[ToolResultBlock(tool_use_id=tool_use_id, tool_name=tool_name, output=output, is_error=is_error)],
        )

    # ── 序列化 ────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        blocks_data = []
        for b in self.blocks:
            if isinstance(b, TextBlock):
                blocks_data.append({"type": "text", "text": b.text})
            elif isinstance(b, ToolUseBlock):
                blocks_data.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
            elif isinstance(b, ToolResultBlock):
                blocks_data.append({
                    "type": "tool_result",
                    "tool_use_id": b.tool_use_id,
                    "tool_name": b.tool_name,
                    "output": b.output,
                    "is_error": b.is_error,
                })
        d: dict[str, Any] = {"role": self.role, "blocks": blocks_data}
        if self.usage:
            d["usage"] = {
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
            }
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ConversationMessage:
        blocks: list[ContentBlock] = []
        for b in d.get("blocks", []):
            t = b["type"]
            if t == "text":
                blocks.append(TextBlock(text=b["text"]))
            elif t == "tool_use":
                blocks.append(ToolUseBlock(id=b["id"], name=b["name"], input=b["input"]))
            elif t == "tool_result":
                blocks.append(ToolResultBlock(
                    tool_use_id=b["tool_use_id"],
                    tool_name=b["tool_name"],
                    output=b["output"],
                    is_error=b.get("is_error", False),
                ))
        usage = None
        if "usage" in d:
            usage = TokenUsage(
                input_tokens=d["usage"].get("input_tokens", 0),
                output_tokens=d["usage"].get("output_tokens", 0),
            )
        return cls(role=d["role"], blocks=blocks, usage=usage)


# ── Session ───────────────────────────────────────────────────────────────────

@dataclass
class Session:
    version: int = 1
    messages: list[ConversationMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Session:
        messages = [ConversationMessage.from_dict(m) for m in d.get("messages", [])]
        return cls(
            version=d.get("version", 1),
            messages=messages,
            created_at=d.get("created_at", time.time()),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Session:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
