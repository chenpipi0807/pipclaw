"""项目选择/创建管理，持久化到 ~/.pipclaw/projects.json。"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

CONFIG_DIR = Path.home() / ".pipclaw"
PROJECTS_FILE = CONFIG_DIR / "projects.json"


@dataclass
class Project:
    name: str
    root: str           # 根目录路径（字符串，方便 JSON 序列化）
    created_at: float
    last_used: float

    @property
    def root_path(self) -> Path:
        return Path(self.root)


def load_projects() -> list[Project]:
    if not PROJECTS_FILE.exists():
        return []
    try:
        data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
        return [Project(**p) for p in data]
    except Exception:
        return []


def save_projects(projects: list[Project]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_FILE.write_text(
        json.dumps([asdict(p) for p in projects], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_project(name: str, root: Path) -> Project:
    projects = load_projects()
    now = time.time()
    proj = Project(name=name, root=str(root.resolve()), created_at=now, last_used=now)
    # 去重（同名同路径）
    projects = [p for p in projects if not (p.name == name and p.root == proj.root)]
    projects.append(proj)
    save_projects(projects)
    return proj


def touch_project(project: Project) -> None:
    """更新 last_used 时间。"""
    projects = load_projects()
    for p in projects:
        if p.name == project.name and p.root == project.root:
            p.last_used = time.time()
    save_projects(projects)


def select_project_cli() -> Project:
    """纯文本 CLI 交互，让用户选择或创建项目（在 Textual 启动前运行）。"""
    projects = sorted(load_projects(), key=lambda p: p.last_used, reverse=True)

    print("\n" + "─" * 50)
    print("  PipClaw — 项目选择")
    print("─" * 50)

    if projects:
        print("\n最近项目：")
        for i, p in enumerate(projects, 1):
            print(f"  [{i}] {p.name}  ({p.root})")
        print(f"\n  [n] 创建新项目")
        print(f"  [q] 退出\n")

        while True:
            choice = input("请选择 > ").strip().lower()
            if choice == "q":
                raise SystemExit(0)
            if choice == "n":
                break
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(projects):
                    proj = projects[idx]
                    touch_project(proj)
                    return proj
            except ValueError:
                pass
            print("无效选择，请重试。")
    else:
        print("\n还没有项目，请创建第一个项目。")

    # 创建新项目
    print("\n创建新项目")
    while True:
        name = input("项目名称 > ").strip()
        if name:
            break
        print("名称不能为空。")

    while True:
        root_str = input("项目根目录（绝对路径或 . 使用当前目录）> ").strip() or "."
        root = Path(root_str).expanduser().resolve()
        if root.exists():
            break
        create = input(f"目录不存在，是否创建？[y/N] > ").strip().lower()
        if create == "y":
            root.mkdir(parents=True, exist_ok=True)
            break
        print("请输入有效路径。")

    proj = add_project(name, root)
    print(f"\n✓ 项目已创建：{name}  ({root})")
    return proj
