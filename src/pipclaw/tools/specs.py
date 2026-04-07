"""工具 JSON Schema 定义（送给 Kimi 模型），对应 claw-code tools/lib.rs mvp_tool_specs()。"""
from __future__ import annotations


def get_tool_specs() -> list[dict]:
    return [
        # ── Kimi 内置工具 ───────────────────────────────────────────────────────
        {
            "type": "builtin_function",
            "function": {"name": "$web_search"},
        },
        # ── 多媒体工具 ──────────────────────────────────────────────────────────
        {
            "type": "function",
            "function": {
                "name": "watch_video_clip",
                "description": "读取本地视频文件（或其中一段），将视频内容发送给模型分析。支持截取片段。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "视频文件路径（绝对路径或相对项目根目录）"},
                        "start_time": {"type": "number", "description": "片段起始时间（秒），默认从头开始"},
                        "end_time": {"type": "number", "description": "片段结束时间（秒），默认到末尾"},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "bash",
                "description": "在项目工作目录执行 shell 命令。适用于运行脚本、安装依赖、git 操作等。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "要执行的 shell 命令"},
                        "timeout": {"type": "integer", "minimum": 1, "description": "超时秒数，默认 30"},
                        "description": {"type": "string", "description": "简要描述该命令的用途"},
                    },
                    "required": ["command"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取工作目录中文件的内容。支持分段读取大文件。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径（相对于项目根目录或绝对路径）"},
                        "offset": {"type": "integer", "minimum": 0, "description": "从第几行开始读取（0 = 从头）"},
                        "limit": {"type": "integer", "minimum": 1, "description": "最多读取多少行"},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "将内容写入文件（覆盖）。文件不存在时自动创建。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "目标文件路径"},
                        "content": {"type": "string", "description": "要写入的完整文件内容"},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "对文件进行精确字符串替换。old_string 在文件中必须唯一。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "要编辑的文件路径"},
                        "old_string": {"type": "string", "description": "要替换的原始字符串（必须在文件中唯一存在）"},
                        "new_string": {"type": "string", "description": "替换后的新字符串"},
                    },
                    "required": ["path", "old_string", "new_string"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "glob_search",
                "description": "按文件名 glob 模式搜索文件，返回匹配的文件路径列表。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "glob 模式，如 '**/*.py' 或 'src/**/*.ts'"},
                        "directory": {"type": "string", "description": "搜索起始目录，默认为项目根目录"},
                    },
                    "required": ["pattern"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "grep_search",
                "description": "在文件内容中搜索正则表达式，返回匹配的行及文件名。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "正则表达式模式"},
                        "directory": {"type": "string", "description": "搜索目录，默认为项目根目录"},
                        "file_glob": {"type": "string", "description": "限制搜索的文件类型，如 '*.py'"},
                        "case_insensitive": {"type": "boolean", "description": "是否忽略大小写，默认 false"},
                    },
                    "required": ["pattern"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "列出目录内容（文件和子目录）。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "要列出的目录路径，默认为项目根目录"},
                        "show_hidden": {"type": "boolean", "description": "是否显示隐藏文件，默认 false"},
                    },
                    "additionalProperties": False,
                },
            },
        },
    ]
