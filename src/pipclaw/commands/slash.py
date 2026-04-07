"""斜杠命令处理，对应 claw-code commands/lib.rs。"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runtime.conversation import ConversationRuntime

SLASH_COMMANDS = {
    "/help": "显示所有可用命令",
    "/clear": "清空当前会话，开启新对话",
    "/status": "显示会话统计（消息数、token 使用）",
    "/cost": "显示累计 token 消耗",
    "/model": "显示当前模型信息",
    "/permissions": "显示当前权限模式",
    "/cd": "切换工作目录（/cd <路径>）",
    "/compact": "手动压缩会话历史（功能待实现）",
    "/n": "新开一个项目（返回项目选择界面）",
    "/q": "退出程序",
}


def is_slash_command(text: str) -> bool:
    return text.startswith("/")


def handle_slash_command(text: str, runtime: ConversationRuntime, app=None) -> str:
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "/help":
        lines = ["可用斜杠命令："]
        for name, desc in SLASH_COMMANDS.items():
            lines.append(f"  {name:<14}  {desc}")
        return "\n".join(lines)

    if cmd == "/clear":
        runtime.clear_session()
        if app:
            import time
            new_id = f"session-{int(time.time())}"
            app._session_id = new_id
            from ..tui.status_bar import StatusBar
            app.query_one("#status-bar", StatusBar).update_session(new_id)
        return "会话已清空，开始新对话。"

    if cmd == "/status":
        msgs = runtime.session.messages
        user_count = sum(1 for m in msgs if m.role == "user")
        assistant_count = sum(1 for m in msgs if m.role == "assistant")
        tool_count = sum(1 for m in msgs if m.role == "tool")
        usage = runtime.cumulative_usage
        return (
            f"会话状态\n"
            f"  消息总数：{len(msgs)}\n"
            f"  用户消息：{user_count}\n"
            f"  助手消息：{assistant_count}\n"
            f"  工具结果：{tool_count}\n"
            f"  累计输入 tokens：{usage.input_tokens:,}\n"
            f"  累计输出 tokens：{usage.output_tokens:,}\n"
            f"  合计：{usage.total_tokens:,}"
        )

    if cmd == "/cost":
        usage = runtime.cumulative_usage
        input_cost = usage.input_tokens / 1_000_000 * 4.00
        output_cost = usage.output_tokens / 1_000_000 * 21.00
        total_cost = input_cost + output_cost
        return (
            f"Token 消耗\n"
            f"  输入：{usage.input_tokens:,} tokens  ≈ ¥{input_cost:.4f}\n"
            f"  输出：{usage.output_tokens:,} tokens  ≈ ¥{output_cost:.4f}\n"
            f"  合计：{usage.total_tokens:,} tokens  ≈ ¥{total_cost:.4f}\n"
            f"  (kimi-k2.5 价格：输入 ¥4/M，输出 ¥21/M)"
        )

    if cmd == "/model":
        return f"当前模型：{runtime.client.model}"

    if cmd == "/permissions":
        mode = runtime.permission_policy.mode.value
        return (
            f"当前权限模式：{mode}\n"
            f"  read-only          — 仅允许读取操作\n"
            f"  workspace-write    — 允许读写文件\n"
            f"  danger-full-access — 允许所有操作（包括 bash）"
        )

    if cmd == "/cd":
        if not arg:
            return "用法：/cd <路径>"
        from pathlib import Path
        new_path = Path(arg).expanduser()
        if not new_path.is_absolute():
            new_path = (runtime.tool_executor.__closure__[0].cell_contents / new_path).resolve()  # type: ignore
        if not new_path.exists() or not new_path.is_dir():
            return f"目录不存在：{new_path}"
        from ..tools.executor import make_executor
        runtime.tool_executor = make_executor(new_path)
        if app:
            from ..tui.file_panel import FilePanel
            app.query_one("#file-panel", FilePanel).set_root(new_path)
        return f"工作目录已切换到：{new_path}"

    if cmd == "/compact":
        return "会话压缩功能即将支持。"

    if cmd == "/q":
        if app:
            app.exit()
        return "正在退出…"

    if cmd == "/n":
        if app:
            app.switch_project()
        return "正在切换项目…"

    return f"未知命令：{cmd}，输入 /help 查看可用命令"
