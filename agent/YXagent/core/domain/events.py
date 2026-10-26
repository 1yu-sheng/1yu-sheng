"""事件契约（UI 无关）。

core 层通过异步事件流把运行过程推送给前端。任何前端（TUI / Web / Desktop / Mobile）
只需要消费 :class:`AgentEvent` 即可渲染，无需了解大模型或工具的具体实现。

事件类型：

======================== ============================================================
事件                     含义
======================== ============================================================
``TurnStarted``          一轮对话开始
``AssistantDelta``       助手回复的流式文本增量
``AssistantCompleted``   助手回复结束（含完整文本）
``ToolCallStarted``      一次工具调用开始
``ToolCallFinished``     一次工具调用结束（含结果与是否成功）
``TurnFinished``         一轮对话结束
``ErrorRaised``          运行期错误
======================== ============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class AgentEventType:
    """事件类型常量（避免使用 Enum，方便 JSON 序列化）。"""

    TURN_STARTED = "turn_started"
    ASSISTANT_DELTA = "assistant_delta"
    ASSISTANT_COMPLETED = "assistant_completed"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_FINISHED = "tool_call_finished"
    TURN_FINISHED = "turn_finished"
    ERROR_RAISED = "error_raised"


@dataclass(frozen=True, slots=True)
class AgentEvent:
    """所有事件的基类。"""

    type: str = field(init=False, default="")

    def __post_init__(self) -> None:  # pragma: no cover - 由子类覆盖
        pass


@dataclass(frozen=True, slots=True)
class TurnStarted(AgentEvent):
    """一轮对话开始。"""

    type: str = field(init=False, default=AgentEventType.TURN_STARTED)
    user_input: str = ""
    turn_id: str = ""


@dataclass(frozen=True, slots=True)
class AssistantDelta(AgentEvent):
    """助手回复的流式文本增量。"""

    type: str = field(init=False, default=AgentEventType.ASSISTANT_DELTA)
    text: str = ""
    turn_id: str = ""


@dataclass(frozen=True, slots=True)
class AssistantCompleted(AgentEvent):
    """助手回复结束。"""

    type: str = field(init=False, default=AgentEventType.ASSISTANT_COMPLETED)
    text: str = ""
    turn_id: str = ""


@dataclass(frozen=True, slots=True)
class ToolCallStarted(AgentEvent):
    """一次工具调用开始。"""

    type: str = field(init=False, default=AgentEventType.TOOL_CALL_STARTED)
    call_id: str = ""
    name: str = ""
    arguments: str = "{}"
    turn_id: str = ""


@dataclass(frozen=True, slots=True)
class ToolCallFinished(AgentEvent):
    """一次工具调用结束。"""

    type: str = field(init=False, default=AgentEventType.TOOL_CALL_FINISHED)
    call_id: str = ""
    name: str = ""
    arguments: str = "{}"
    result: str = ""
    ok: bool = True
    turn_id: str = ""


@dataclass(frozen=True, slots=True)
class TurnFinished(AgentEvent):
    """一轮对话结束。"""

    type: str = field(init=False, default=AgentEventType.TURN_FINISHED)
    turn_id: str = ""
    rounds: int = 0
    stopped_reason: str = "completed"


@dataclass(frozen=True, slots=True)
class ErrorRaised(AgentEvent):
    """运行期错误。"""

    type: str = field(init=False, default=AgentEventType.ERROR_RAISED)
    message: str = ""
    detail: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "AgentEvent",
    "AgentEventType",
    "AssistantCompleted",
    "AssistantDelta",
    "ErrorRaised",
    "ToolCallFinished",
    "ToolCallStarted",
    "TurnFinished",
    "TurnStarted",
]
