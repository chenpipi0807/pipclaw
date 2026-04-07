"""权限策略，对应 claw-code runtime/permissions.rs。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class PermissionMode(Enum):
    READ_ONLY = "read-only"
    WORKSPACE_WRITE = "workspace-write"
    DANGER_FULL_ACCESS = "danger-full-access"


# 工具所需的最低权限级别
TOOL_REQUIRED_PERMISSION: dict[str, PermissionMode] = {
    "bash": PermissionMode.DANGER_FULL_ACCESS,
    "write_file": PermissionMode.WORKSPACE_WRITE,
    "edit_file": PermissionMode.WORKSPACE_WRITE,
    "read_file": PermissionMode.READ_ONLY,
    "glob_search": PermissionMode.READ_ONLY,
    "grep_search": PermissionMode.READ_ONLY,
    "list_dir": PermissionMode.READ_ONLY,
}

_PERMISSION_LEVEL = {
    PermissionMode.READ_ONLY: 0,
    PermissionMode.WORKSPACE_WRITE: 1,
    PermissionMode.DANGER_FULL_ACCESS: 2,
}


@dataclass
class PermissionOutcome:
    allowed: bool
    reason: str = ""


# 交互式确认回调类型：(tool_name, input_json) -> bool
PermissionPrompter = Callable[[str, str], bool]


class PermissionPolicy:
    def __init__(
        self,
        mode: PermissionMode = PermissionMode.WORKSPACE_WRITE,
        prompter: PermissionPrompter | None = None,
    ) -> None:
        self.mode = mode
        self.prompter = prompter

    def authorize(self, tool_name: str, input_json: str) -> PermissionOutcome:
        required = TOOL_REQUIRED_PERMISSION.get(tool_name, PermissionMode.DANGER_FULL_ACCESS)

        if _PERMISSION_LEVEL[self.mode] >= _PERMISSION_LEVEL[required]:
            return PermissionOutcome(allowed=True)

        # 当前模式不够，但有交互提示器时让用户决定
        if self.prompter:
            allowed = self.prompter(tool_name, input_json)
            if allowed:
                return PermissionOutcome(allowed=True)
            return PermissionOutcome(allowed=False, reason=f"用户拒绝了工具调用：{tool_name}")

        return PermissionOutcome(
            allowed=False,
            reason=f"工具 '{tool_name}' 需要 '{required.value}' 权限，当前为 '{self.mode.value}'",
        )
