"""搜索工具：glob_search, grep_search。"""
from __future__ import annotations

import json
import re
from pathlib import Path


def glob_search(input_json: str, cwd: Path) -> str:
    args = json.loads(input_json)
    pattern: str = args["pattern"]
    directory = Path(args["directory"]) if "directory" in args else cwd
    if not directory.is_absolute():
        directory = (cwd / directory).resolve()

    try:
        matches = sorted(directory.glob(pattern))
    except Exception as e:
        return f"[glob 失败] {e}"

    if not matches:
        return f"没有找到匹配 '{pattern}' 的文件"

    lines = []
    for p in matches[:500]:  # 最多返回 500 条
        try:
            rel = p.relative_to(cwd)
        except ValueError:
            rel = p
        lines.append(str(rel))

    result = "\n".join(lines)
    if len(matches) > 500:
        result += f"\n... [共 {len(matches)} 个结果，只显示前 500 个]"
    return result


def grep_search(input_json: str, cwd: Path) -> str:
    args = json.loads(input_json)
    pattern: str = args["pattern"]
    directory = Path(args.get("directory", "."))
    if not directory.is_absolute():
        directory = (cwd / directory).resolve()

    file_glob: str = args.get("file_glob", "*")
    case_insensitive: bool = args.get("case_insensitive", False)

    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"[无效正则] {e}"

    results: list[str] = []
    try:
        files = list(directory.rglob(file_glob))
    except Exception as e:
        return f"[搜索失败] {e}"

    for filepath in files:
        if not filepath.is_file():
            continue
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                try:
                    rel = filepath.relative_to(cwd)
                except ValueError:
                    rel = filepath
                results.append(f"{rel}:{lineno}:{line.rstrip()}")
                if len(results) >= 200:
                    break
        if len(results) >= 200:
            break

    if not results:
        return f"没有找到匹配 '{pattern}' 的内容"

    output = "\n".join(results)
    if len(results) >= 200:
        output += "\n... [结果过多，已截断]"
    return output
