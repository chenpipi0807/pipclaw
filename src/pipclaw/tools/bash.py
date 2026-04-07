"""bash 工具：在项目目录执行 shell 命令。"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

DEFAULT_TIMEOUT = 30
MAX_OUTPUT = 20_000  # 最多返回字符数，避免撑爆上下文


def run_bash(input_json: str, cwd: Path) -> str:
    args = json.loads(input_json)
    command: str = args["command"]
    timeout: int = args.get("timeout", DEFAULT_TIMEOUT)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return f"[超时] 命令超过 {timeout} 秒未完成：{command}"
    except Exception as e:
        return f"[执行失败] {e}"

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    combined = stdout
    if stderr:
        combined += f"\n[stderr]\n{stderr}"

    if len(combined) > MAX_OUTPUT:
        combined = combined[:MAX_OUTPUT] + f"\n... [输出截断，共 {len(combined)} 字符]"

    if result.returncode != 0:
        combined += f"\n[退出码 {result.returncode}]"

    return combined.strip() or f"[命令执行成功，无输出，退出码 {result.returncode}]"
