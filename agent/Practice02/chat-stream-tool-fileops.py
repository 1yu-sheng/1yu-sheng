import configparser
import json
import mimetypes
import os
import shutil
import subprocess
import sys

from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8")

MAX_TOOL_ROUNDS = 8
MAX_READ_CHARS = 8000


def getDate() -> str:
    """获取当前电脑的日期和时间，调用本地系统命令 date /t 和 time /t"""
    date_str = ""
    time_str = ""

    try:
        try:
            result = subprocess.run(
                ["date", "/t"],
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            date_str = result.stdout.strip()
        except Exception:
            result = subprocess.run(
                ["cmd", "/c", "date", "/t"],
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            date_str = result.stdout.strip()
    except Exception as e:
        date_str = f"获取日期失败: {e}"

    try:
        try:
            result = subprocess.run(
                ["time", "/t"],
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            time_str = result.stdout.strip()
        except Exception:
            result = subprocess.run(
                ["cmd", "/c", "time", "/t"],
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            time_str = result.stdout.strip()
    except Exception as e:
        time_str = f"获取时间失败: {e}"

    return f"{date_str} {time_str}".strip()


def isLeapYear(year: int) -> bool:
    """判断输入的年份是否是闰年"""
    y = int(year)
    if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):
        return True
    return False


def getWorkingDirectory() -> str:
    """获取当前工作目录"""
    return os.getcwd()


def listDirectory(path: str) -> str:
    """列出指定目录下的所有文件和子目录"""
    if not path or not path.strip():
        return "错误: 目录路径不能为空"
    target = path.strip()
    if not os.path.isdir(target):
        return f"错误: 目录不存在: {target}"
    lines = []
    try:
        with os.scandir(target) as entries:
            for entry in sorted(entries, key=lambda e: (not e.is_dir(), e.name.lower())):
                if entry.is_dir(follow_symlinks=False):
                    lines.append(f"[DIR]  {entry.name}/")
                else:
                    try:
                        size = os.path.getsize(entry.path)
                    except OSError:
                        size = -1
                    lines.append(f"[FILE] {entry.name} ({size} bytes)")
    except PermissionError:
        return f"错误: 没有权限访问目录: {target}"
    if not lines:
        return f"目录为空: {os.path.abspath(target)}"
    return "\n".join(lines)


def getFileType(path: str) -> str:
    """获取指定文件的文件类型"""
    if not path or not path.strip():
        return "错误: 文件路径不能为空"
    target = path.strip()
    if not os.path.isfile(target):
        return f"错误: 文件不存在: {target}"
    ext = os.path.splitext(target)[1] or "(无扩展名)"
    mime, _ = mimetypes.guess_type(target)
    kind = "未知"
    try:
        with open(target, "rb") as f:
            head = f.read(8192)
        if b"\x00" in head:
            kind = "二进制文件"
        else:
            try:
                head.decode("utf-8")
                kind = "文本文件(UTF-8)"
            except UnicodeDecodeError:
                kind = "文本文件(其他编码)"
    except OSError as e:
        return f"错误: 无法读取文件: {e}"
    size = os.path.getsize(target)
    return f"扩展名: {ext}, MIME类型: {mime or '未知'}, 内容类型: {kind}, 大小: {size} 字节"


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别的文本编码")


def readFile(path: str) -> str:
    """获取指定文件的内容（仅支持纯文本格式文件）"""
    if not path or not path.strip():
        return "错误: 文件路径不能为空"
    target = path.strip()
    if not os.path.isfile(target):
        return f"错误: 文件不存在: {target}"
    try:
        with open(target, "rb") as f:
            data = f.read()
    except OSError as e:
        return f"错误: 无法读取文件: {e}"
    if b"\x00" in data:
        return f"错误: {target} 是二进制文件，仅支持读取纯文本格式文件"
    try:
        text = _decode_text(data)
    except ValueError as e:
        return f"错误: {e}"
    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + f"\n...(已截断，文件共 {len(text)} 字符)"
    return text


def createFile(directory: str, filename: str, content: str = "") -> str:
    """根据指定的目录和文件名创建新文件"""
    if not directory or not directory.strip():
        return "错误: 目录路径不能为空"
    if not filename or not filename.strip():
        return "错误: 文件名不能为空"
    full_path = os.path.join(directory.strip(), filename.strip())
    if os.path.exists(full_path):
        return f"错误: 文件已存在: {full_path}"
    try:
        os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content or "")
    except OSError as e:
        return f"错误: 创建文件失败: {e}"
    return f"已创建文件: {os.path.abspath(full_path)}"


def editFile(path: str, content: str) -> str:
    """编辑指定文件的内容（仅支持纯文本格式文件），用新内容覆盖原文件"""
    if not path or not path.strip():
        return "错误: 文件路径不能为空"
    target = path.strip()
    if not os.path.isfile(target):
        return f"错误: 文件不存在: {target}"
    try:
        with open(target, "rb") as f:
            data = f.read()
    except OSError as e:
        return f"错误: 无法读取文件: {e}"
    if b"\x00" in data:
        return f"错误: {target} 是二进制文件，仅支持编辑纯文本格式文件"
    try:
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write(content if content is not None else "")
    except OSError as e:
        return f"错误: 写入文件失败: {e}"
    return f"已编辑文件: {os.path.abspath(target)}，新内容 {len(content or '')} 个字符"


def createDirectory(path: str) -> str:
    """创建新目录"""
    if not path or not path.strip():
        return "错误: 目录路径不能为空"
    target = path.strip()
    if os.path.exists(target):
        return f"错误: 路径已存在: {target}"
    try:
        os.makedirs(target)
    except OSError as e:
        return f"错误: 创建目录失败: {e}"
    return f"已创建目录: {os.path.abspath(target)}"


def _check_not_root(path: str) -> str:
    abs_path = os.path.abspath(path)
    drive = os.path.splitdrive(abs_path)[0]
    root = drive + os.sep
    if abs_path.lower() == root.lower():
        raise ValueError(f"拒绝操作驱动器根目录: {abs_path}")
    return abs_path


def removeDirectory(path: str) -> str:
    """删除目录及其全部内容（支持非空目录）"""
    if not path or not path.strip():
        return "错误: 目录路径不能为空"
    target = _check_not_root(path.strip())
    if not os.path.isdir(target):
        return f"错误: 目录不存在: {target}"
    try:
        shutil.rmtree(target)
    except OSError as e:
        return f"错误: 删除目录失败: {e}"
    return f"已删除目录(含全部内容): {target}"


def deleteFile(path: str) -> str:
    """删除指定文件"""
    if not path or not path.strip():
        return "错误: 文件路径不能为空"
    target = _check_not_root(path.strip())
    if not os.path.isfile(target):
        return f"错误: 文件不存在: {target}"
    try:
        os.remove(target)
    except OSError as e:
        return f"错误: 删除文件失败: {e}"
    return f"已删除文件: {target}"


def renamePath(path: str, new_name: str) -> str:
    """重命名指定的文件或目录"""
    if not path or not path.strip():
        return "错误: 原路径不能为空"
    if not new_name or not new_name.strip():
        return "错误: 新名称不能为空"
    target = _check_not_root(path.strip())
    if not os.path.exists(target):
        return f"错误: 文件或目录不存在: {target}"
    if os.path.sep in new_name.strip() or (os.path.altsep and os.path.altsep in new_name.strip()):
        return "错误: 新名称不能包含路径分隔符，只能是文件名或目录名"
    new_path = os.path.join(os.path.dirname(target), new_name.strip())
    if os.path.exists(new_path):
        return f"错误: 新名称对应的路径已存在: {new_path}"
    try:
        os.rename(target, new_path)
    except OSError as e:
        return f"错误: 重命名失败: {e}"
    kind = "目录" if os.path.isdir(new_path) else "文件"
    return f"已重命名{kind}: {target} -> {new_path}"


def runTool(name: str, args: dict) -> str:
    try:
        if name == "getDate":
            return getDate()
        if name == "isLeapYear":
            return "是闰年" if isLeapYear(args.get("year")) else "不是闰年"
        if name == "getWorkingDirectory":
            return getWorkingDirectory()
        if name == "listDirectory":
            return listDirectory(args.get("path", ""))
        if name == "getFileType":
            return getFileType(args.get("path", ""))
        if name == "readFile":
            return readFile(args.get("path", ""))
        if name == "createFile":
            return createFile(
                args.get("directory", ""),
                args.get("filename", ""),
                args.get("content", ""),
            )
        if name == "editFile":
            return editFile(args.get("path", ""), args.get("content", ""))
        if name == "createDirectory":
            return createDirectory(args.get("path", ""))
        if name == "removeDirectory":
            return removeDirectory(args.get("path", ""))
        if name == "deleteFile":
            return deleteFile(args.get("path", ""))
        if name == "renamePath":
            return renamePath(args.get("path", ""), args.get("new_name", ""))
        return f"未知工具: {name}"
    except Exception as e:
        return f"工具执行失败: {e}"


PATH_PARAM = {
    "type": "string",
    "description": "文件或目录的路径",
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "getDate",
            "description": "获取当前电脑的日期和时间。调用本地系统命令 date /t 和 time /t 获取日期和时间",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "isLeapYear",
            "description": "计算输入的年份是否是闰年",
            "parameters": {
                "type": "object",
                "properties": {"year": {"type": "integer", "description": "要判断的年份"}},
                "required": ["year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "getWorkingDirectory",
            "description": "获取当前工作目录的路径",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listDirectory",
            "description": "列出指定目录下的所有文件和子目录",
            "parameters": {
                "type": "object",
                "properties": {"path": PATH_PARAM},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "getFileType",
            "description": "获取指定文件的文件类型（扩展名、MIME类型、文本或二进制）",
            "parameters": {
                "type": "object",
                "properties": {"path": PATH_PARAM},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "readFile",
            "description": "获取指定文件的内容，仅支持纯文本格式文件",
            "parameters": {
                "type": "object",
                "properties": {"path": PATH_PARAM},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "createFile",
            "description": "根据指定的目录和文件名创建新文件，可选写入初始内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "新文件所在的目录路径"},
                    "filename": {"type": "string", "description": "新文件的文件名"},
                    "content": {"type": "string", "description": "文件的初始内容，可选，默认为空"},
                },
                "required": ["directory", "filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "editFile",
            "description": "编辑指定文件的内容（仅支持纯文本格式文件），用新内容覆盖原文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": PATH_PARAM,
                    "content": {"type": "string", "description": "文件的新内容"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "createDirectory",
            "description": "创建新目录",
            "parameters": {
                "type": "object",
                "properties": {"path": PATH_PARAM},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "removeDirectory",
            "description": "删除指定目录及其全部内容（非空目录也可以删除）",
            "parameters": {
                "type": "object",
                "properties": {"path": PATH_PARAM},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deleteFile",
            "description": "删除指定文件",
            "parameters": {
                "type": "object",
                "properties": {"path": PATH_PARAM},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "renamePath",
            "description": "重命名指定的文件或目录，新名称只能是文件名或目录名，不能包含路径",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": PATH_PARAM,
                    "new_name": {"type": "string", "description": "新的文件名或目录名（不含路径）"},
                },
                "required": ["path", "new_name"],
            },
        },
    },
]

cp = configparser.ConfigParser()
with open("config.ini", encoding="utf-8") as f:
    cp.read_string("[llm]\n" + f.read())

base_url = cp.get("llm", "base_url").strip('"')
api_key = cp.get("llm", "api_key").strip('"')
model = cp.get("llm", "model").strip('"')

client = OpenAI(base_url=base_url, api_key=api_key)
messages = []

while True:
    try:
        print("please input your prompt")
        user_input = input()
        messages.append({"role": "user", "content": user_input})
    except (EOFError, KeyboardInterrupt):
        break
    print("--")

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                stream=True,
            )

            reply = ""
            tool_calls_acc = {}
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta is None:
                    continue
                if delta.content:
                    print(delta.content, end="", flush=True)
                    reply += delta.content
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        entry = tool_calls_acc.setdefault(
                            tc.index,
                            {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
                        )
                        if tc.id:
                            entry["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                entry["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                entry["function"]["arguments"] += tc.function.arguments

            if not tool_calls_acc:
                messages.append({"role": "assistant", "content": reply})
                print()
                break

            tool_calls = [tool_calls_acc[k] for k in sorted(tool_calls_acc)]
            for i, tc in enumerate(tool_calls):
                if not tc["id"]:
                    tc["id"] = f"call_{i}"
            messages.append({"role": "assistant", "content": reply or None, "tool_calls": tool_calls})
            if reply:
                print()

            for tc in tool_calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError as e:
                    result = f"参数解析失败: {e}"
                else:
                    print(f"\n[tool] {name} args={args}", flush=True)
                    result = runTool(name, args)
                print(f"[tool] {name} -> {result}", flush=True)
                messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": result}
                )
        else:
            print("\n(达到最大工具调用轮次，停止)")
    except Exception as e:
        print(f"error: {e}")
