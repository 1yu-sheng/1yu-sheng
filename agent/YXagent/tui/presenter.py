"""TUI 表现层：把 core 事件翻译成界面更新动作。

这一层的存在让 :mod:`tui.widgets` 与 :mod:`tui.screens` 不需要直接依赖 core 内部结构，
同时保证"换一个前端只需重写表现层"的扩展路径。
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core import (
    AgentEvent,
    AgentEventType,
    AssistantCompleted,
    AssistantDelta,
    ErrorRaised,
    ToolCallFinished,
    ToolCallStarted,
    TurnFinished,
    TurnStarted,
)


@dataclass
class TurnViewState:
    """当前轮次的视图状态。"""

    turn_id: str = ""
    user_input: str = ""
    assistant_text: str = ""
    rounds: int = 0
    stopped_reason: str = ""
    is_running: bool = False
    tool_calls: list[tuple[str, str]] = field(default_factory=list)


class AgentPresenter:
    """把 :class:`AgentEvent` 转换为可回调的视图动作。

    每个动作都是一个普通回调，TUI 用它更新控件；
    未来的 Web / Desktop 前端则可以用它驱动状态管理或 DOM 更新。
    """

    def __init__(self) -> None:
        self._turn_started: list[Callable[[TurnStarted], Any]] = []
        self._assistant_delta: list[Callable[[AssistantDelta], Any]] = []
        self._assistant_completed: list[Callable[[AssistantCompleted], Any]] = []
        self._tool_started: list[Callable[[ToolCallStarted], Any]] = []
        self._tool_finished: list[Callable[[ToolCallFinished], Any]] = []
        self._turn_finished: list[Callable[[TurnFinished], Any]] = []
        self._error: list[Callable[[ErrorRaised], Any]] = []

    # ------------------------------------------------------------------
    # 订阅
    # ------------------------------------------------------------------
    def on_turn_started(self, callback: Callable[[TurnStarted], Any]) -> None:
        self._turn_started.append(callback)

    def on_assistant_delta(self, callback: Callable[[AssistantDelta], Any]) -> None:
        self._assistant_delta.append(callback)

    def on_assistant_completed(self, callback: Callable[[AssistantCompleted], Any]) -> None:
        self._assistant_completed.append(callback)

    def on_tool_started(self, callback: Callable[[ToolCallStarted], Any]) -> None:
        self._tool_started.append(callback)

    def on_tool_finished(self, callback: Callable[[ToolCallFinished], Any]) -> None:
        self._tool_finished.append(callback)

    def on_turn_finished(self, callback: Callable[[TurnFinished], Any]) -> None:
        self._turn_finished.append(callback)

    def on_error(self, callback: Callable[[ErrorRaised], Any]) -> None:
        self._error.append(callback)

    # ------------------------------------------------------------------
    # 分发
    # ------------------------------------------------------------------
    async def dispatch(self, event: AgentEvent) -> None:
        """把一个事件分发给所有订阅者。

        订阅者可以是同步函数，也可以是协程函数；协程会被等待执行完毕，
        因此界面更新可以安全地使用 ``await``（例如挂载控件）。
        """
        for callback in self._callbacks_for(event):
            result = callback(event)
            if inspect.isawaitable(result):
                await result

    def _callbacks_for(self, event: AgentEvent) -> list[Callable[[AgentEvent], Any]]:
        """按事件类型取出对应的订阅者。"""
        event_type = event.type
        if event_type == AgentEventType.TURN_STARTED:
            return list(self._turn_started)
        if event_type == AgentEventType.ASSISTANT_DELTA:
            return list(self._assistant_delta)
        if event_type == AgentEventType.ASSISTANT_COMPLETED:
            return list(self._assistant_completed)
        if event_type == AgentEventType.TOOL_CALL_STARTED:
            return list(self._tool_started)
        if event_type == AgentEventType.TOOL_CALL_FINISHED:
            return list(self._tool_finished)
        if event_type == AgentEventType.TURN_FINISHED:
            return list(self._turn_finished)
        if event_type == AgentEventType.ERROR_RAISED:
            return list(self._error)
        return []


__all__ = ["AgentPresenter", "TurnViewState"]
