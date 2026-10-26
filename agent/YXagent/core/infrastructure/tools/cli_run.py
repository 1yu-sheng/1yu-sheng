"""CLI 调用工具。

允许 Agent 调用本地已安装的任意命令行程序（教学实验用）。
"""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any

from core.domain.models import ToolSpec
from core.infrastructure.tools.base import FunctionTool


class RunCliTool(FunctionTool):
    """使用 subprocess 调用本地 CLI 程序。"""

    def __init__(self, *, timeout: float = 60.0, max_output_chars: int = 8000) -> None:
        self._timeout = timeout
        self._max_output_chars = max_output_chars

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="RunCli",
            description=(
                "调用本地已安装的命令行程序。传入程序名称 command 和参数列表 args，"
                "使用参数列表方式（shell=False）执行。"
                "返回标准输出（stdout）、标准错误（stderr）和退出码（exit code），"
                "便于根据执行结果决定下一步操作。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的程序名称或可执行文件路径",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "传递给程序的参数列表（不包含程序本身）",
                        "default": [],
                    },
                },
                "required": ["command"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        command = arguments.get("command")
        if not isinstance(command, str) or not command.strip():
            return "执行失败：缺少必填参数 command（程序名称或可执行文件路径）。"

        args_raw = arguments.get("args", [])
        if args_raw is None:
            args = []
        elif isinstance(args_raw, list):
            args = [str(a) for a in args_raw]
        else:
            return "执行失败：args 必须是字符串数组。"

        cmd_list = [command.strip()] + args

        try:
            result = await asyncio.to_thread(self._execute, cmd_list)
        except subprocess.TimeoutExpired:
            return f"执行失败：命令超时（{self._timeout:g} 秒）。"
        except FileNotFoundError:
            return f"执行失败：未找到可执行程序：{command.strip()}"
        except OSError as exc:
            return f"执行失败：执行命令时发生系统错误（{exc}）。"
        except Exception as exc:  # noqa: BLE001
            return f"执行失败：执行命令时发生异常（{type(exc).__name__}: {exc}）。"

        stdout = result.stdout
        stderr = result.stderr
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        stdout = stdout or ""
        stderr = stderr or ""

        def _truncate(text: str, label: str) -> tuple[str, bool]:
            if len(text) <= self._max_output_chars:
                return text, False
            truncated = text[: self._max_output_chars]
            return truncated + f"\n\n……（{label}内容过长，已截断，未显示全部）", True

        stdout_trunc, stdout_cut = _truncate(stdout, "stdout")
        stderr_trunc, stderr_cut = _truncate(stderr, "stderr")
        cut_any = stdout_cut or stderr_cut

        lines = [
            f"命令：{cmd_list}",
            f"退出码（exit code）：{result.returncode}",
            "",
            "标准输出（stdout）：",
            stdout_trunc if stdout_trunc else "（空）",
            "",
            "标准错误（stderr）：",
            stderr_trunc if stderr_trunc else "（空）",
        ]
        if cut_any:
            lines.append("")
            lines.append("（注意：部分输出因过长已截断）")
        return "\n".join(lines)

    def _execute(self, cmd_list: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self._timeout,
            check=False,
            shell=False,
        )


__all__ = ["RunCliTool"]
