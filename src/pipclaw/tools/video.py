"""视频工具：将本地视频文件编码为 base64 发送给 Kimi 模型分析。"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path


def watch_video_clip(input_json: str, cwd: Path) -> list[dict]:
    """
    读取视频文件（或片段），返回多模态内容块列表。
    返回格式：[{"type": "video_url", "video_url": {"url": "data:video/mp4;base64,..."}}, {"type": "text", ...}]
    """
    args = json.loads(input_json)
    raw_path = args["path"]
    start_time: float | None = args.get("start_time")
    end_time: float | None = args.get("end_time")

    # 解析路径（支持相对路径）
    p = Path(raw_path)
    if not p.is_absolute():
        p = cwd / p
    p = p.resolve()

    if not p.exists():
        raise FileNotFoundError(f"视频文件不存在：{p}")

    ext = p.suffix.lower().lstrip(".")
    mime = f"video/{ext}" if ext != "mkv" else "video/x-matroska"

    if start_time is None and end_time is None:
        # 整个视频
        video_bytes = p.read_bytes()
        label = f"完整视频：{p.name}"
    else:
        # 用 ffmpeg 截取片段
        video_bytes, label = _extract_clip(p, start_time or 0, end_time)

    video_b64 = base64.b64encode(video_bytes).decode("utf-8")
    video_url = f"data:{mime};base64,{video_b64}"

    return [
        {"type": "video_url", "video_url": {"url": video_url}},
        {"type": "text", "text": label},
    ]


def _extract_clip(path: Path, start: float, end: float | None) -> tuple[bytes, str]:
    import shutil
    if not shutil.which("ffmpeg"):
        raise RuntimeError("未找到 ffmpeg，无法截取视频片段。请安装 ffmpeg 或不指定 start_time/end_time。")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        cmd = ["ffmpeg", "-y", "-ss", str(start), "-i", str(path)]
        if end is not None:
            cmd += ["-t", str(end - start)]
        cmd += ["-c:v", "libx264", "-c:a", "aac", "-preset", "fast",
                "-crf", "23", "-movflags", "+faststart", "-loglevel", "error", tmp_path]
        subprocess.run(cmd, check=True)

        data = Path(tmp_path).read_bytes()
        label = f"视频片段：{path.name}  {start}s → {end or '末尾'}"
        return data, label
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
