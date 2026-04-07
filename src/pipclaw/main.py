"""PipClaw 入口：加载 .env → 项目选择 → 启动 TUI。"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    # 加载 .env（优先从当前目录，其次从脚本目录）
    _load_env()

    if "MOONSHOT_API_KEY" not in os.environ:
        print("错误：未找到 MOONSHOT_API_KEY。请在 .env 文件中设置，或通过环境变量导出。")
        sys.exit(1)

    from .project.manager import select_project_cli
    from .tui.app import PipClawApp

    # 主循环：/n 会让 TUI 退出并重新进入项目选择
    while True:
        try:
            project = select_project_cli()
        except KeyboardInterrupt:
            print("\n已退出。")
            sys.exit(0)

        app = PipClawApp(
            project_root=project.root_path,
            project_name=project.name,
        )
        app.run()

        # 若不是 /n 触发的切换，则正常退出
        if not getattr(app, "_switch_to_new_project", False):
            break


def _load_env() -> None:
    """尝试从多个位置加载 .env 文件。"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    candidates = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent / ".env",  # 项目根目录
        Path.home() / ".pipclaw" / ".env",
    ]
    for p in candidates:
        if p.exists():
            load_dotenv(p)
            break


if __name__ == "__main__":
    main()
