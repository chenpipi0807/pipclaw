"""文件操作工具：read_file, write_file, edit_file, list_dir。"""
from __future__ import annotations

import json
from pathlib import Path


def read_file(input_json: str, cwd: Path) -> str:
    args = json.loads(input_json)
    path = _resolve(args["path"], cwd)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{path}")
    if path.is_dir():
        raise IsADirectoryError(f"路径是目录，请使用 list_dir：{path}")

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except Exception as e:
        return f"[读取失败] {e}"

    offset = args.get("offset", 0)
    limit = args.get("limit")
    selected = lines[offset:offset + limit] if limit else lines[offset:]

    numbered = [f"{offset + i + 1}\t{line}" for i, line in enumerate(selected)]
    return "".join(numbered) or "(空文件)"


def write_file(input_json: str, cwd: Path) -> str:
    args = json.loads(input_json)
    path = _resolve(args["path"], cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"], encoding="utf-8")
    return f"已写入 {path}（{len(args['content'])} 字符）"


def edit_file(input_json: str, cwd: Path) -> str:
    args = json.loads(input_json)
    path = _resolve(args["path"], cwd)
    old = args["old_string"]
    new = args["new_string"]

    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{path}")

    content = path.read_text(encoding="utf-8")
    count = content.count(old)

    if count == 0:
        raise ValueError(f"old_string 在文件中未找到：{path}")
    if count > 1:
        raise ValueError(f"old_string 在文件中出现 {count} 次（必须唯一）：{path}")

    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    return f"已编辑 {path}"


def list_dir(input_json: str, cwd: Path) -> str:
    args = json.loads(input_json) if input_json.strip() else {}
    path = _resolve(args.get("path", "."), cwd)
    show_hidden = args.get("show_hidden", False)

    if not path.exists():
        raise FileNotFoundError(f"目录不存在：{path}")
    if not path.is_dir():
        raise NotADirectoryError(f"不是目录：{path}")

    entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    lines = []
    for entry in entries:
        if not show_hidden and entry.name.startswith("."):
            continue
        suffix = "/" if entry.is_dir() else ""
        size = ""
        if entry.is_file():
            try:
                sz = entry.stat().st_size
                size = f"  {_human_size(sz)}"
            except OSError:
                pass
        lines.append(f"{'[dir] ' if entry.is_dir() else '      '}{entry.name}{suffix}{size}")

    return "\n".join(lines) or "(空目录)"


def _resolve(p: str, cwd: Path) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (cwd / path).resolve()


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n //= 1024
    return f"{n:.0f}TB"
