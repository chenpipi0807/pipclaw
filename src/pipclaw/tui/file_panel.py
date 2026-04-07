"""右侧文件管理面板：单击选中，双击预览，按钮打开 yazi。"""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DirectoryTree, Label, RichLog

from .preview import render_preview, fullscreen_preview

DOUBLE_CLICK_MS = 400  # 双击间隔阈值（毫秒）


class PathSelected(Message):
    """用户按 y 将路径发送给对话区。"""
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path


class FilePanel(Widget):
    """右侧文件管理器：单击选中，双击预览，按钮打开 yazi。"""

    _selected: Path | None = None
    _last_click_path: Path | None = None
    _last_click_ts: float = 0.0

    def __init__(self, root: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._root = root

    def compose(self) -> ComposeResult:
        with Vertical(id="file-container"):
            yield Label(id="file-root-label")
            yield Button("📂  在 Yazi 中打开当前目录/文件", id="btn-yazi", variant="default")
            yield DirectoryTree(str(self._root), id="file-tree-area")
            yield Label("预览  （双击文件显示）", id="preview-label")
            yield RichLog(id="preview-area", highlight=False, markup=False, wrap=False)

    def on_mount(self) -> None:
        self._update_root_label()

    # ── 鼠标事件：单击选中 / 双击预览 ────────────────────────────────────────

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        path = Path(str(event.path))
        now = time.time() * 1000  # ms

        is_double = (
            path == self._last_click_path
            and (now - self._last_click_ts) < DOUBLE_CLICK_MS
        )

        self._selected = path
        self._last_click_path = path
        self._last_click_ts = now

        if is_double:
            # 双击 → 预览
            self._last_click_ts = 0.0  # 重置，避免三击也触发
            self._show_preview(path)
        else:
            # 单击 → 仅在状态区显示路径，不加载预览
            self._show_selected_hint(path)

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        path = Path(str(event.path))
        now = time.time() * 1000

        is_double = (
            path == self._last_click_path
            and (now - self._last_click_ts) < DOUBLE_CLICK_MS
        )

        self._selected = path
        self._last_click_path = path
        self._last_click_ts = now

        if is_double:
            self._last_click_ts = 0.0
            self._show_dir_preview(path)
        else:
            self._show_selected_hint(path)

    # ── 按钮：打开 yazi ───────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-yazi":
            self.open_yazi()

    def open_yazi(self) -> None:
        if not shutil.which("yazi"):
            self._write_preview([
                Text("未找到 yazi 可执行文件", style="#f85149"),
                Text("请确认 yazi.exe 已加入 PATH，然后重开终端", style="#8b949e"),
            ])
            return
        start = self._selected or self._root
        with self.app.suspend():
            subprocess.run(["yazi", str(start)])
        self.refresh_tree()

    # ── 公开方法 ──────────────────────────────────────────────────────────────

    def refresh_tree(self) -> None:
        self.query_one("#file-tree-area", DirectoryTree).reload()

    def set_root(self, path: Path) -> None:
        self._root = path
        self._update_root_label()
        tree = self.query_one("#file-tree-area", DirectoryTree)
        tree.path = str(path)
        tree.reload()

    # ── 内部渲染 ──────────────────────────────────────────────────────────────

    def _show_selected_hint(self, path: Path) -> None:
        """单击：只在预览区显示文件名和提示，不加载内容。"""
        t = Text()
        t.append(path.name, style="bold #58a6ff")
        suffix = "  (目录)" if path.is_dir() else f"  {path.suffix or ''}"
        t.append(suffix, style="#8b949e")
        hint = Text("双击查看预览", style="italic #6e7681")
        self._write_preview([t, hint])

    def _show_preview(self, path: Path) -> None:
        """双击 → 暂停 TUI，全屏高清预览，按任意键返回。"""
        # 先在面板显示"加载中"提示
        self._write_preview([
            Text(path.name, style="bold #58a6ff"),
            Text("全屏预览加载中…", style="italic #6e7681"),
        ])
        with self.app.suspend():
            fullscreen_preview(path)

    def _show_dir_preview(self, path: Path) -> None:
        lines: list[Text] = []
        t = Text()
        t.append(str(path), style="bold #58a6ff")
        t.append("  (目录)", style="#8b949e")
        lines.append(t)
        lines.append(Text(""))
        try:
            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for entry in entries[:80]:
                if entry.name.startswith("."):
                    continue
                row = Text()
                row.append("📁 " if entry.is_dir() else "📄 ")
                row.append(entry.name, style="#c9d1d9")
                lines.append(row)
            if len(entries) > 80:
                lines.append(Text(f"… 共 {len(entries)} 个条目", style="#8b949e"))
        except PermissionError:
            lines.append(Text("权限不足", style="#f85149"))
        self._write_preview(lines)

    def _write_preview(self, lines: list[Text]) -> None:
        log = self.query_one("#preview-area", RichLog)
        log.clear()
        for line in lines:
            log.write(line)

    def _update_root_label(self) -> None:
        label = self.query_one("#file-root-label", Label)
        t = Text()
        t.append("📁 ", style="")
        t.append(str(self._root), style="bold #58a6ff")
        label.update(t)
