"""应用层：Agent 编排与会话管理。

本层是 core 的业务核心，**完全 UI 无关**。
所有前端（TUI / Web / Desktop / Mobile）都通过 :class:`AgentService`
这一唯一入口驱动 Agent，并消费 :class:`~core.domain.events.AgentEvent` 事件流。
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Sequence

from core.config import AgentConfig
from core.domain.events import (
    AgentEvent,
    AssistantCompleted,
    AssistantDelta,
    ErrorRaised,
    ToolCallFinished,
    ToolCallStarted,
    TurnFinished,
    TurnStarted,
)
from core.domain.models import Message, ToolCall, ToolCallDelta, ToolSpec
from core.ports.llm import LLMClient
from core.ports.tools import ToolRegistry


class Session:
    """一次会话（一条对话线）的上下文与元数据。"""

    def __init__(self, session_id: str | None = None, title: str = "") -> None:
        self.id = session_id or uuid.uuid4().hex
        self.title = title
        self.messages: list[Message] = []
        self.created_at = uuid.uuid4().hex

    def clear(self) -> None:
        """清空历史消息。"""
        self.messages.clear()

    def summary(self) -> dict[str, object]:
        """返回会话摘要信息（供前端展示）。"""
        return {
            "id": self.id,
            "title": self.title,
            "message_count": len(self.messages),
        }


class AgentService:
    """Agent 应用服务：core 层对外唯一门面。

    职责：

    * 维护会话上下文；
    * 驱动"模型 → 工具 → 模型"的循环；
    * 把整个过程转换为 UI 无关的事件流。

    前端只需：

    .. code-block:: python

        async for event in service.run_turn("你好"):
            render(event)
    """

    def __init__(
        self,
        llm: LLMClient,
        tools: ToolRegistry,
        config: AgentConfig | None = None,
        session: Session | None = None,
    ) -> None:
        self._llm = llm
        self._tools = tools
        self._config = config or AgentConfig()
        self._session = session or Session()

    @property
    def session(self) -> Session:
        """当前会话。"""
        return self._session

    @property
    def tools(self) -> ToolRegistry:
        """工具注册表。"""
        return self._tools

    def new_session(self) -> Session:
        """开启一个新会话并返回。"""
        self._session = Session()
        return self._session

    def reset(self) -> None:
        """清空当前会话历史。"""
        self._session.clear()

    def tool_specs(self) -> list[ToolSpec]:
        """返回工具声明（供前端展示"可用工具"）。"""
        return self._tools.specs()

    async def aclose(self) -> None:
        """释放底层资源（如大模型客户端的 HTTP 连接）。"""
        await self._llm.close()

    async def run_turn(self, user_input: str) -> AsyncIterator[AgentEvent]:
        """执行一轮对话，产出事件流。

        Args:
            user_input: 用户输入。

        Yields:
            :class:`AgentEvent` 事件序列。
        """
        turn_id = uuid.uuid4().hex
        yield TurnStarted(user_input=user_input, turn_id=turn_id)

        self._session.messages.append(Message(role="user", content=user_input))

        try:
            async for event in self._run_turn_body(turn_id):
                yield event
        except Exception as exc:  # noqa: BLE001 - 顶层兜底，转成事件交给前端展示
            yield ErrorRaised(message=str(exc), detail={"type": type(exc).__name__})

    async def _run_turn_body(self, turn_id: str) -> AsyncIterator[AgentEvent]:
        """工具调用循环。"""
        rounds = 0
        stopped_reason = "completed"

        while rounds < self._config.max_tool_rounds:
            rounds += 1
            reply_parts: list[str] = []
            tool_deltas: dict[int, ToolCallDelta] = {}

            async for chunk in self._llm.stream_chat(self._history(), self._tools.specs()):
                if chunk.content:
                    reply_parts.append(chunk.content)
                    yield AssistantDelta(text=chunk.content, turn_id=turn_id)
                for delta in chunk.tool_calls or ():
                    tool_deltas[delta.index] = _merge_delta(tool_deltas.get(delta.index), delta)

            reply = "".join(reply_parts)
            tool_calls = _finalize_tool_calls(tool_deltas)

            if not tool_calls:
                self._session.messages.append(Message(role="assistant", content=reply))
                yield AssistantCompleted(text=reply, turn_id=turn_id)
                break

            self._session.messages.append(
                Message(role="assistant", content=reply or None, tool_calls=tuple(tool_calls))
            )

            for call in tool_calls:
                yield ToolCallStarted(
                    call_id=call.id,
                    name=call.name,
                    arguments=call.arguments,
                    turn_id=turn_id,
                )
                result, ok = await self._execute_tool(call)
                self._session.messages.append(
                    Message(role="tool", content=result, tool_call_id=call.id)
                )
                yield ToolCallFinished(
                    call_id=call.id,
                    name=call.name,
                    arguments=call.arguments,
                    result=result,
                    ok=ok,
                    turn_id=turn_id,
                )
        else:
            stopped_reason = "max_tool_rounds"

        yield TurnFinished(turn_id=turn_id, rounds=rounds, stopped_reason=stopped_reason)

    async def _execute_tool(self, call: ToolCall) -> tuple[str, bool]:
        """执行单个工具，返回 ``(结果文本, 是否成功)``。"""
        import json

        try:
            arguments = json.loads(call.arguments or "{}")
        except json.JSONDecodeError as exc:
            return f"参数解析失败: {exc}", False

        if not isinstance(arguments, dict):
            return "参数解析失败: 工具参数必须是 JSON 对象", False

        tool = self._tools.get(call.name)
        if tool is None:
            return f"未知工具: {call.name}", False

        try:
            return await tool.execute(arguments), True
        except Exception as exc:  # noqa: BLE001 - 工具异常不应中断整轮对话
            return f"工具执行失败: {exc}", False

    def _history(self) -> Sequence[Message]:
        """构造发送给模型的上下文（含系统提示词）。"""
        history: list[Message] = []
        if self._config.system_prompt:
            history.append(Message(role="system", content=self._config.system_prompt))
        history.extend(self._session.messages)
        return history


def _merge_delta(current: ToolCallDelta | None, delta: ToolCallDelta) -> ToolCallDelta:
    """合并同一个工具调用的流式增量。"""
    if current is None:
        return ToolCallDelta(
            index=delta.index,
            id=delta.id or None,
            name=delta.name or None,
            arguments=delta.arguments,
        )
    return ToolCallDelta(
        index=current.index,
        id=current.id or delta.id or None,
        name=current.name or delta.name or None,
        arguments=current.arguments + delta.arguments,
    )


def _finalize_tool_calls(deltas: dict[int, ToolCallDelta]) -> list[ToolCall]:
    """把累积的增量整理为有序的完整工具调用列表。"""
    calls: list[ToolCall] = []
    for position, index in enumerate(sorted(deltas)):
        delta = deltas[index]
        call_id = delta.id or f"call_{position}"
        calls.append(
            ToolCall(
                id=call_id,
                name=delta.name or "",
                arguments=delta.arguments or "{}",
            )
        )
    return calls


__all__ = ["AgentService", "Session"]
