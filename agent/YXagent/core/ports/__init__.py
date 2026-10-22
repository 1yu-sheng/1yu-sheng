"""端口层：定义 core 与外部世界之间的抽象契约。"""

from core.ports.llm import LLMClient
from core.ports.tools import Tool, ToolRegistry

__all__ = ["LLMClient", "Tool", "ToolRegistry"]
