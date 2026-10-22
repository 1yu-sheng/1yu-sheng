"""工具实现的公共基类。

把"声明 + 执行"从重复的样板代码中抽离出来，让每个具体工具只聚焦业务逻辑。
"""

from __future__ import annotations

from typing import Any

from core.domain.models import ToolSpec
from core.ports.tools import Tool


class FunctionTool(Tool):
    """由一组固定参数声明驱动的简单工具。

    子类只需提供 :meth:`spec` 与 :meth:`run`。
    """

    @property
    def spec(self) -> ToolSpec:
        raise NotImplementedError

    async def execute(self, arguments: dict[str, Any]) -> str:
        """执行工具；异常会被上层捕获并转成错误文本回填给模型。"""
        return await self.run(arguments)

    async def run(self, arguments: dict[str, Any]) -> str:
        raise NotImplementedError


def path_parameter(description: str = "文件或目录的路径") -> dict[str, Any]:
    """生成通用的路径参数声明。"""
    return {"type": "string", "description": description}


__all__ = ["FunctionTool", "path_parameter"]
