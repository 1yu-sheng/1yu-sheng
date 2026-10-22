"""领域模型（纯数据结构，不依赖任何框架）。

这些模型是 core 层与所有前端（TUI / Web / Desktop / Mobile）之间共享的数据契约。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True, slots=True)
class ToolCall:
    """一次完整的工具调用请求。"""

    id: str
    name: str
    arguments: str = "{}"
    """模型给出的原始 JSON 参数串。"""

    @property
    def parsed_arguments(self) -> dict[str, Any]:
        """把原始参数串解析为字典，解析失败时返回空字典。"""
        import json

        try:
            parsed = json.loads(self.arguments or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}


@dataclass(frozen=True, slots=True)
class ToolCallDelta:
    """流式过程中片段化的工具调用增量。"""

    index: int
    id: str | None = None
    name: str | None = None
    arguments: str = ""


@dataclass(frozen=True, slots=True)
class ToolResult:
    """工具执行结果。"""

    call_id: str
    name: str
    text: str
    ok: bool = True


@dataclass(slots=True)
class Message:
    """一条对话消息。"""

    role: Role
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None

    def to_wire(self) -> dict[str, Any]:
        """转换为 OpenAI 兼容的请求体片段。"""
        if self.role == "tool":
            return {
                "role": "tool",
                "tool_call_id": self.tool_call_id or "",
                "content": self.content or "",
            }
        if self.tool_calls:
            return {
                "role": self.role,
                "content": self.content or None,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": call.arguments},
                    }
                    for call in self.tool_calls
                ],
            }
        return {"role": self.role, "content": self.content or ""}


@dataclass(slots=True)
class ToolSpec:
    """工具的声明信息（provider 无关）。"""

    name: str
    description: str
    parameters: Mapping[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})

    def to_openai_schema(self) -> dict[str, Any]:
        """转换为 OpenAI function-calling 风格的工具声明。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": dict(self.parameters),
            },
        }
