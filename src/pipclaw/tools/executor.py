"""工具分发器：将工具名称路由到具体实现。"""
from __future__ import annotations

from pathlib import Path

from .bash import run_bash
from .file_ops import edit_file, list_dir, read_file, write_file
from .search import glob_search, grep_search
from .video import watch_video_clip

_TOOL_MAP = {
    "bash": run_bash,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "glob_search": glob_search,
    "grep_search": grep_search,
    "list_dir": list_dir,
    "watch_video_clip": watch_video_clip,
}


def make_executor(cwd: Path):
    """返回绑定了工作目录的工具执行函数。
    返回值可以是 str（普通文本结果）或 list[dict]（多模态内容块）。
    """

    def execute(tool_name: str, input_json: str) -> str | list:
        fn = _TOOL_MAP.get(tool_name)
        if fn is None:
            raise ValueError(f"未知工具：{tool_name}")
        return fn(input_json, cwd)

    return execute
