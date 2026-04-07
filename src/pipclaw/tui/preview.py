"""文件预览：图片/视频帧用 PIL+Unicode 半块字符彩色渲染，音频/PDF/代码显示元数据和文本。"""
from __future__ import annotations

import mimetypes
import subprocess
import tempfile
from pathlib import Path

from rich.text import Text

_CODE_EXT: dict[str, str] = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".rs": "rust", ".go": "go",
    ".java": "java", ".c": "c", ".cpp": "cpp", ".h": "c",
    ".cs": "csharp", ".rb": "ruby", ".php": "php", ".swift": "swift",
    ".kt": "kotlin", ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".ps1": "powershell", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".ini": "ini", ".cfg": "ini",
    ".md": "markdown", ".html": "html", ".css": "css",
    ".xml": "xml", ".sql": "sql", ".lua": "lua",
    ".txt": "text", ".log": "text", ".csv": "text",
}

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".ico", ".tiff"}
_VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mpg", ".mpeg", ".wmv", ".flv"}
_AUDIO_EXT = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".opus"}
_PDF_EXT   = {".pdf"}

# 预览图最大宽度（字符数），高度自动按比例缩放
# 右侧面板约占终端宽度的 40%，72 会超出导致行折叠损坏图像
PREVIEW_WIDTH = 48


def render_preview(path: Path, max_width: int = PREVIEW_WIDTH) -> list[Text]:
    if not path.exists():
        return [Text(f"文件不存在：{path}", style="#f85149")]
    ext = path.suffix.lower()
    try:
        if ext in _CODE_EXT:
            return _render_code(path, _CODE_EXT[ext])
        if ext in _IMAGE_EXT:
            return _render_image(path, max_width)
        if ext in _VIDEO_EXT:
            return _render_video(path, max_width)
        if ext in _AUDIO_EXT:
            return _render_audio(path)
        if ext in _PDF_EXT:
            return _render_pdf(path, max_width)
        return _render_hex(path)
    except Exception as e:
        return [Text(f"预览失败：{e}", style="#f85149")]


# ── 图片：PIL → Unicode 半块字符彩色渲染 ──────────────────────────────────────

def _pil_to_block_art(img, max_width: int = PREVIEW_WIDTH) -> list[Text]:
    """
    用 ▀（上半块）实现每字符 2 行像素：
      前景色 = 上像素颜色，背景色 = 下像素颜色
    效果：在支持 256/True Color 的终端里看到彩色图片缩略图。
    """
    from PIL import Image

    img = img.convert("RGB")
    w = min(max_width, img.width)
    # 字符高宽比约 2:1，所以像素高度 = 字符高 × 2
    char_h = max(1, int(w * img.height / img.width / 2))
    # 最多显示 24 行，避免撑爆预览区
    char_h = min(char_h, 24)
    img = img.resize((w, char_h * 2), Image.LANCZOS)
    px = img.load()

    lines: list[Text] = []
    for cy in range(char_h):
        row = Text()
        for cx in range(w):
            r1, g1, b1 = px[cx, cy * 2]
            r2, g2, b2 = px[cx, cy * 2 + 1]
            row.append(
                "▀",
                style=f"#{r1:02x}{g1:02x}{b1:02x} on #{r2:02x}{g2:02x}{b2:02x}",
            )
        lines.append(row)
    return lines


def _render_image(path: Path, max_width: int = PREVIEW_WIDTH) -> list[Text]:
    lines: list[Text] = [_header(path)]
    try:
        from PIL import Image
        img = Image.open(path)
        w, h = img.size
        mode = img.mode
        lines.append(Text(f"尺寸：{w} × {h}   模式：{mode}   大小：{_human_size(path.stat().st_size)}", style="#8b949e"))
        lines.append(Text(""))
        lines.extend(_pil_to_block_art(img, max_width))
    except ImportError:
        lines.append(Text("提示：pip install Pillow 后可显示图片预览", style="#6e7681"))
    except Exception as e:
        lines.append(Text(f"图片读取失败：{e}", style="#f85149"))
    return lines


# ── 视频：ffmpeg 提取第一帧 → PIL 渲染 ───────────────────────────────────────

def _render_video(path: Path, max_width: int = PREVIEW_WIDTH) -> list[Text]:
    import shutil
    lines: list[Text] = [_header(path)]

    # 先尝试读取视频元数据
    if shutil.which("ffprobe"):
        try:
            import json
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", str(path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=10,
            )
            if result.stdout and result.stdout.strip():
                data = json.loads(result.stdout)
                fmt = data.get("format", {})
                dur = float(fmt.get("duration") or 0)
                bps = int(fmt.get("bit_rate") or 0)
                lines.append(Text(f"时长：{_fmt_duration(dur)}   比特率：{bps // 1000} kbps", style="#8b949e"))
                for s in data.get("streams", []):
                    if s.get("codec_type") == "video":
                        codec = s.get("codec_name", "?")
                        w, h = s.get("width", "?"), s.get("height", "?")
                        fps_raw = s.get("r_frame_rate", "0/1")
                        try:
                            n, d = fps_raw.split("/")
                            fps = round(int(n) / int(d), 1)
                        except Exception:
                            fps = "?"
                        lines.append(Text(f"视频流：{w}×{h}   编码：{codec}   帧率：{fps} fps", style="#8b949e"))
        except Exception as e:
            lines.append(Text(f"元数据读取失败：{e}", style="#f85149"))
    else:
        lines.append(Text(f"大小：{_human_size(path.stat().st_size)}   类型：视频 ({path.suffix})", style="#8b949e"))
        lines.append(Text("提示：安装 ffmpeg 可显示视频详情和首帧预览", style="#6e7681"))

    # 提取第一帧缩略图
    if shutil.which("ffmpeg"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            subprocess.run(
                ["ffmpeg", "-y", "-ss", "0", "-i", str(path),
                 "-frames:v", "1", "-q:v", "2", tmp_path],
                capture_output=True, timeout=15,
            )
            frame_path = Path(tmp_path)
            if frame_path.exists() and frame_path.stat().st_size > 0:
                from PIL import Image
                img = Image.open(frame_path)
                lines.append(Text(""))
                lines.append(Text("首帧预览：", style="#8b949e"))
                lines.extend(_pil_to_block_art(img, max_width))
                frame_path.unlink(missing_ok=True)
        except ImportError:
            lines.append(Text("提示：pip install Pillow 后可显示首帧预览", style="#6e7681"))
        except Exception as e:
            lines.append(Text(f"首帧提取失败：{e}", style="#f85149"))

    return lines


# ── 音频 ──────────────────────────────────────────────────────────────────────

def _render_audio(path: Path) -> list[Text]:
    lines: list[Text] = [_header(path)]
    try:
        import mutagen
        audio = mutagen.File(path)
        if audio and hasattr(audio, "info"):
            dur = getattr(audio.info, "length", 0)
            br  = getattr(audio.info, "bitrate", 0)
            lines.append(Text(f"时长：{_fmt_duration(dur)}   比特率：{br} kbps", style="#8b949e"))
        tags = getattr(audio, "tags", None) if audio else None
        if tags:
            for key, label in [
                ("TIT2", "标题"), ("title", "标题"),
                ("TPE1", "艺术家"), ("artist", "艺术家"),
                ("TALB", "专辑"), ("album", "专辑"),
                ("TDRC", "年份"), ("date", "年份"),
            ]:
                val = tags.get(key)
                if val:
                    lines.append(Text(f"{label}：{val}", style="#c9d1d9"))
    except ImportError:
        lines.append(Text("提示：pip install mutagen 可显示音频元数据", style="#6e7681"))
    except Exception as e:
        lines.append(Text(f"读取失败：{e}", style="#f85149"))
    return lines


# ── 代码/文本 ─────────────────────────────────────────────────────────────────

def _render_code(path: Path, _lang: str) -> list[Text]:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [Text(f"读取失败：{e}", style="#f85149")]
    all_lines = content.splitlines()
    result: list[Text] = [_header(path), Text("")]
    for i, line in enumerate(all_lines[:200], 1):
        row = Text()
        row.append(f"{i:4d} ", style="#4d5566")
        row.append(line, style="#c9d1d9")
        result.append(row)
    if len(all_lines) > 200:
        result.append(Text(f"… 共 {len(all_lines)} 行，只显示前 200 行", style="#8b949e"))
    return result


# ── PDF ───────────────────────────────────────────────────────────────────────

def _render_pdf(path: Path, max_width: int = PREVIEW_WIDTH) -> list[Text]:
    lines: list[Text] = [_header(path), Text("类型：PDF", style="#8b949e")]
    try:
        import fitz
        doc = fitz.open(str(path))
        lines.append(Text(f"页数：{len(doc)}", style="#8b949e"))
        for key, label in [("title", "标题"), ("author", "作者"), ("subject", "主题")]:
            if doc.metadata.get(key):
                lines.append(Text(f"{label}：{doc.metadata[key]}", style="#c9d1d9"))
        # 第一页渲染为图片
        try:
            from PIL import Image
            import io
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            lines.append(Text(""))
            lines.append(Text("第一页预览：", style="#8b949e"))
            lines.extend(_pil_to_block_art(img, max_width))
        except ImportError:
            text = doc[0].get_text()[:600].strip()
            if text:
                lines.append(Text(""))
                lines.append(Text("第一页文本：", style="#8b949e"))
                for ln in text.splitlines()[:20]:
                    lines.append(Text(ln, style="#c9d1d9"))
        doc.close()
    except ImportError:
        lines.append(Text("提示：pip install pymupdf 可预览 PDF", style="#6e7681"))
    except Exception as e:
        lines.append(Text(f"读取失败：{e}", style="#f85149"))
    return lines


# ── 二进制/未知 ───────────────────────────────────────────────────────────────

def _render_hex(path: Path) -> list[Text]:
    mime, _ = mimetypes.guess_type(str(path))
    lines: list[Text] = [
        _header(path),
        Text(f"类型：{mime or '未知'}   大小：{_human_size(path.stat().st_size)}", style="#8b949e"),
        Text(""),
        Text("Hex dump（前 256 字节）：", style="#8b949e"),
    ]
    try:
        raw = path.read_bytes()[:256]
        for i in range(0, len(raw), 16):
            chunk = raw[i:i + 16]
            row = Text()
            row.append(f"{i:04x}  ", style="#4d5566")
            row.append(" ".join(f"{b:02x}" for b in chunk).ljust(48) + "  ", style="#8b949e")
            row.append("".join(chr(b) if 32 <= b < 127 else "." for b in chunk), style="#c9d1d9")
            lines.append(row)
    except OSError as e:
        lines.append(Text(f"读取失败：{e}", style="#f85149"))
    return lines


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _header(path: Path) -> Text:
    t = Text()
    t.append(path.name, style="bold #58a6ff")
    try:
        t.append(f"  {_human_size(path.stat().st_size)}", style="#8b949e")
    except OSError:
        pass
    return t


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n //= 1024
    return f"{n:.0f} TB"


def _fmt_duration(s: float) -> str:
    s = int(s)
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


# ── 全屏预览（暂停 TUI，接管终端，按任意键返回） ────────────────────────────────

def fullscreen_preview(path: Path) -> None:
    """
    暂停 TUI 后调用此函数，在裸终端全屏渲染文件。
    - 图片/视频帧：优先 term_image（自动 Sixel/Kitty/halfblock）
    - 音频：rich 元数据表格
    - 代码/文本：rich Syntax 高亮
    - PDF：第一页渲染
    - 其他：hex dump
    按任意键后返回。
    """
    import os, sys, shutil
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    ext = path.suffix.lower()

    console.clear()
    console.print(f"[bold #58a6ff]{path.name}[/]  [#8b949e]{_human_size(path.stat().st_size)}[/]")
    console.print()

    try:
        if ext in _IMAGE_EXT:
            _fs_image(path, console)
        elif ext in _VIDEO_EXT:
            _fs_video(path, console)
        elif ext in _AUDIO_EXT:
            _fs_audio(path, console)
        elif ext in _PDF_EXT:
            _fs_pdf(path, console)
        elif ext in _CODE_EXT:
            _fs_code(path, console)
        else:
            _fs_hex(path, console)
    except Exception as e:
        console.print(f"[#f85149]预览失败：{e}[/]")

    console.print()
    console.print("[italic #6e7681]按任意键返回…[/]", end="")
    sys.stdout.flush()
    _wait_key()
    console.clear()


def _wait_key() -> None:
    import sys, os
    if os.name == "nt":
        import msvcrt
        msvcrt.getch()
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _fs_image(path: Path, console) -> None:
    try:
        from term_image.image import AutoImage
        img = AutoImage(str(path))
        # 全终端宽度，最大高度 40 行
        img.set_size(h_allow=2, v_allow=4)
        img.draw()
        return
    except Exception:
        pass
    # fallback：PIL halfblock，使用全终端宽度
    try:
        import shutil as _sh
        from PIL import Image
        tw = _sh.get_terminal_size().columns - 2
        img = Image.open(path)
        lines = _pil_to_block_art(img, max_width=tw)
        from rich.text import Text
        for line in lines:
            console.print(line)
    except Exception as e:
        console.print(f"[#f85149]{e}[/]")


def _fs_video(path: Path, console) -> None:
    import shutil as _sh
    # 元数据
    if _sh.which("ffprobe"):
        try:
            import json
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", str(path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
            )
            if r.stdout.strip():
                data = json.loads(r.stdout)
                fmt = data.get("format", {})
                dur = float(fmt.get("duration") or 0)
                bps = int(fmt.get("bit_rate") or 0)
                console.print(f"[#8b949e]时长：{_fmt_duration(dur)}   比特率：{bps//1000} kbps[/]")
                for s in data.get("streams", []):
                    if s.get("codec_type") == "video":
                        console.print(f"[#8b949e]视频流：{s.get('width')}×{s.get('height')}   "
                                      f"编码：{s.get('codec_name')}   帧率：{s.get('r_frame_rate')}[/]")
        except Exception as e:
            console.print(f"[#f85149]元数据读取失败：{e}[/]")

    # 首帧
    if _sh.which("ffmpeg"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            subprocess.run(
                ["ffmpeg", "-y", "-ss", "0", "-i", str(path),
                 "-frames:v", "1", "-q:v", "2", tmp_path],
                capture_output=True, timeout=15,
            )
            frame = Path(tmp_path)
            if frame.exists() and frame.stat().st_size > 0:
                console.print()
                _fs_image(frame, console)
                frame.unlink(missing_ok=True)
        except Exception as e:
            console.print(f"[#f85149]首帧提取失败：{e}[/]")
    else:
        console.print("[#6e7681]提示：安装 ffmpeg 可显示首帧预览[/]")


def _fs_audio(path: Path, console) -> None:
    try:
        import mutagen
        from rich.table import Table
        audio = mutagen.File(path)
        t = Table(show_header=False, box=None, padding=(0, 1))
        if audio and hasattr(audio, "info"):
            dur = getattr(audio.info, "length", 0)
            br  = getattr(audio.info, "bitrate", 0)
            t.add_row("[#8b949e]时长[/]", f"{_fmt_duration(dur)}")
            t.add_row("[#8b949e]比特率[/]", f"{br} kbps")
        tags = getattr(audio, "tags", None) if audio else None
        if tags:
            for key, label in [
                ("TIT2", "标题"), ("title", "标题"),
                ("TPE1", "艺术家"), ("artist", "艺术家"),
                ("TALB", "专辑"), ("album", "专辑"),
            ]:
                val = tags.get(key)
                if val:
                    t.add_row(f"[#8b949e]{label}[/]", str(val))
                    break  # 只取第一个匹配
        console.print(t)
    except ImportError:
        console.print("[#6e7681]pip install mutagen 可显示音频元数据[/]")
    except Exception as e:
        console.print(f"[#f85149]{e}[/]")


def _fs_code(path: Path, console) -> None:
    from rich.syntax import Syntax
    lang = _CODE_EXT.get(path.suffix.lower(), "text")
    try:
        code = path.read_text(encoding="utf-8", errors="replace")
        syntax = Syntax(code, lang, theme="github-dark", line_numbers=True,
                        word_wrap=False)
        console.print(syntax)
    except Exception as e:
        console.print(f"[#f85149]{e}[/]")


def _fs_pdf(path: Path, console) -> None:
    try:
        import fitz
        doc = fitz.open(str(path))
        console.print(f"[#8b949e]页数：{len(doc)}[/]")
        for k, label in [("title","标题"),("author","作者")]:
            if doc.metadata.get(k):
                console.print(f"[#8b949e]{label}：[/]{doc.metadata[k]}")
        from PIL import Image
        import io
        import shutil as _sh
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        console.print()
        _fs_image_pil(img, console)
        doc.close()
    except ImportError:
        console.print("[#6e7681]pip install pymupdf 可预览 PDF[/]")
    except Exception as e:
        console.print(f"[#f85149]{e}[/]")


def _fs_image_pil(img, console) -> None:
    import shutil as _sh
    tw = _sh.get_terminal_size().columns - 2
    lines = _pil_to_block_art(img, max_width=tw)
    for line in lines:
        console.print(line)


def _fs_hex(path: Path, console) -> None:
    from rich.table import Table
    mime, _ = mimetypes.guess_type(str(path))
    console.print(f"[#8b949e]类型：{mime or '未知'}[/]")
    console.print()
    raw = path.read_bytes()[:512]
    for i in range(0, len(raw), 16):
        chunk = raw[i:i+16]
        hex_part = " ".join(f"{b:02x}" for b in chunk).ljust(48)
        asc_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        console.print(f"[#4d5566]{i:04x}[/]  [#8b949e]{hex_part}[/]  [#c9d1d9]{asc_part}[/]")
