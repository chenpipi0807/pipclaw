"""工具层单元测试。"""
import json
import tempfile
from pathlib import Path

import pytest

from kimi_agent.tools.file_ops import edit_file, list_dir, read_file, write_file
from kimi_agent.tools.search import glob_search, grep_search


@pytest.fixture
def tmp(tmp_path):
    return tmp_path


def test_write_and_read(tmp):
    write_file(json.dumps({"path": "hello.txt", "content": "Hello, World!\n"}), tmp)
    result = read_file(json.dumps({"path": "hello.txt"}), tmp)
    assert "Hello, World!" in result


def test_read_with_offset_limit(tmp):
    lines = "\n".join(f"line {i}" for i in range(10))
    write_file(json.dumps({"path": "lines.txt", "content": lines}), tmp)
    result = read_file(json.dumps({"path": "lines.txt", "offset": 2, "limit": 3}), tmp)
    assert "line 2" in result
    assert "line 4" in result
    assert "line 5" not in result


def test_edit_file(tmp):
    write_file(json.dumps({"path": "f.py", "content": "x = 1\n"}), tmp)
    edit_file(json.dumps({"path": "f.py", "old_string": "x = 1", "new_string": "x = 42"}), tmp)
    content = (tmp / "f.py").read_text()
    assert "x = 42" in content


def test_edit_file_not_unique(tmp):
    write_file(json.dumps({"path": "f.py", "content": "x = 1\nx = 1\n"}), tmp)
    with pytest.raises(ValueError, match="唯一"):
        edit_file(json.dumps({"path": "f.py", "old_string": "x = 1", "new_string": "x = 2"}), tmp)


def test_list_dir(tmp):
    (tmp / "a.py").write_text("a")
    (tmp / "subdir").mkdir()
    result = list_dir("{}", tmp)
    assert "subdir" in result
    assert "a.py" in result


def test_glob_search(tmp):
    (tmp / "a.py").write_text("a")
    (tmp / "b.py").write_text("b")
    (tmp / "c.txt").write_text("c")
    result = glob_search(json.dumps({"pattern": "*.py"}), tmp)
    assert "a.py" in result
    assert "b.py" in result
    assert "c.txt" not in result


def test_grep_search(tmp):
    (tmp / "code.py").write_text("def hello():\n    pass\n")
    result = grep_search(json.dumps({"pattern": "def \\w+"}), tmp)
    assert "code.py" in result
    assert "hello" in result
