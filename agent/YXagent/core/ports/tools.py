"""工具端口（Port）。

工具是 core 层对"外部能力"的抽象。一个工具实现三个要素：

* ``spec``  —— 声明（名称、描述、JSON Schema），会暴露给大模型；
* ``execute`` —— 真正的执行逻辑；
* 返回值 —— 一段文本，会被回填给大模型作为 tool 消息。

新增工具只需实现 :class:`Tool` 并注册到 :class:`ToolRegistry`，
前端与 Agent 循环无需任何改动。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.domain.models import ToolSpec


class Tool(ABC):
    """可被大模型调用的工具。"""

    @property
    @abstractmethod
    def spec(self) -> ToolSpec:
        """工具声明。"""
        raise NotImplementedError

    @abstractmethod
    async def execute(self, arguments: dict[str, Any]) -> str:
        """执行工具并返回给模型的文本结果。"""
        raise NotImplementedError


class ToolRegistry:
    """工具注册表：负责声明聚合与按名称分发。"""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        """注册一个工具（同名工具会覆盖旧实现）。"""
        self._tools[tool.spec.name] = tool

    def unregister(self, name: str) -> None:
        """移除一个工具。"""
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        """按名称查找工具。"""
        return self._tools.get(name)

    def specs(self) -> list[ToolSpec]:
        """返回全部工具声明（顺序稳定，便于测试）。"""
        return [tool.spec for tool in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: object) -> bool:
        return name in self._tools


__all__ = ["Tool", "ToolRegistry"]
