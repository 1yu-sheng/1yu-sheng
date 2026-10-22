"""日期与时间相关工具。"""

from __future__ import annotations

import subprocess
from typing import Any

from core.domain.models import ToolSpec
from core.infrastructure.tools.base import FunctionTool


class GetDateTool(FunctionTool):
    """获取当前电脑的日期和时间。"""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="getDate",
            description="获取当前电脑的日期和时间。调用本地系统命令 date /t 和 time /t 获取日期和时间",
            parameters={"type": "object", "properties": {}, "required": []},
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        return f"{_run_date()} {_run_time()}".strip()


class IsLeapYearTool(FunctionTool):
    """判断年份是否为闰年。"""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="isLeapYear",
            description="计算输入的年份是否是闰年",
            parameters={
                "type": "object",
                "properties": {"year": {"type": "integer", "description": "要判断的年份"}},
                "required": ["year"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        raw_year = arguments.get("year")
        try:
            year = int(raw_year)
        except (TypeError, ValueError):
            return f"错误: 年份参数无效: {raw_year!r}"
        return "是闰年" if _is_leap_year(year) else "不是闰年"


def _is_leap_year(year: int) -> bool:
    """判断年份是否为闰年。"""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def _run_date() -> str:
    """调用系统命令获取日期。"""
    return _run_system_date_time("date", "/t", "获取日期失败")


def _run_time() -> str:
    """调用系统命令获取时间。"""
    return _run_system_date_time("time", "/t", "获取时间失败")


def _run_system_date_time(command: str, argument: str, error_prefix: str) -> str:
    """执行 ``command argument``，失败时退回 ``cmd /c`` 形式。"""
    try:
        try:
            result = subprocess.run(
                [command, argument],
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError):
            result = subprocess.run(
                ["cmd", "/c", command, argument],
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        return result.stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"{error_prefix}: {exc}"


__all__ = ["GetDateTool", "IsLeapYearTool"]
