"""应用层（AgentService）测试。"""

from __future__ import annotations

from core.application.agent_service import AgentService
from core.config import AgentConfig
from core.domain.events import AgentEventType
from core.ports.tools import ToolRegistry
from tests.conftest import ScriptedLLMClient, text_chunk, tool_chunk


async def collect(service: AgentService, user_input: str) -> list:
    """收集一轮对话产生的全部事件。"""
    return [event async for event in service.run_turn(user_input)]


async def test_simple_turn_emits_expected_events():
    client = ScriptedLLMClient([[text_chunk("你好"), text_chunk("！")]])
    service = AgentService(llm=client, tools=ToolRegistry(), config=AgentConfig())

    events = await collect(service, "hi")

    types = [event.type for event in events]
    assert types[0] == AgentEventType.TURN_STARTED
    assert types[-1] == AgentEventType.TURN_FINISHED
    assert AgentEventType.ASSISTANT_DELTA in types
    assert AgentEventType.ASSISTANT_COMPLETED in types

    completed = next(e for e in events if e.type == AgentEventType.ASSISTANT_COMPLETED)
    assert completed.text == "你好！"


async def test_tool_call_round_trips_result_to_model():
    class EchoTool:
        @property
        def spec(self):
            from core.domain.models import ToolSpec

            return ToolSpec(name="echo", description="回显", parameters={})

        async def execute(self, arguments):
            return f"echo:{arguments.get('value')}"

    client = ScriptedLLMClient(
        [
            [tool_chunk(0, "call_1", "echo", '{"value": "x"}')],
            [text_chunk("完成")],
        ]
    )
    registry = ToolRegistry([EchoTool()])
    service = AgentService(llm=client, tools=registry, config=AgentConfig())

    events = await collect(service, "调用工具")

    started = next(e for e in events if e.type == AgentEventType.TOOL_CALL_STARTED)
    finished = next(e for e in events if e.type == AgentEventType.TOOL_CALL_FINISHED)
    assert started.name == "echo"
    assert finished.result == "echo:x"
    assert finished.ok is True

    # tool 结果应回填进下一次模型请求的上下文
    second_call_messages = client.calls[1]
    tool_messages = [m for m in second_call_messages if m.role == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0].content == "echo:x"
    assert tool_messages[0].tool_call_id == "call_1"


async def test_unknown_tool_is_reported_not_raised():
    client = ScriptedLLMClient(
        [
            [tool_chunk(0, "call_1", "missing", "{}")],
            [text_chunk("好的")],
        ]
    )
    service = AgentService(llm=client, tools=ToolRegistry(), config=AgentConfig())

    events = await collect(service, "调用不存在的工具")

    finished = next(e for e in events if e.type == AgentEventType.TOOL_CALL_FINISHED)
    assert finished.ok is False
    assert "未知工具" in finished.result


async def test_max_tool_rounds_stops_loop():
    class NeverEnding:
        @property
        def spec(self):
            from core.domain.models import ToolSpec

            return ToolSpec(name="loop", description="循环", parameters={})

        async def execute(self, arguments):
            return "again"

    client = ScriptedLLMClient(
        [[tool_chunk(0, f"call_{i}", "loop", "{}")] for i in range(10)]
    )
    registry = ToolRegistry([NeverEnding()])
    service = AgentService(
        llm=client, tools=registry, config=AgentConfig(max_tool_rounds=3)
    )

    events = await collect(service, "一直调用")

    finished = next(e for e in events if e.type == AgentEventType.TURN_FINISHED)
    assert finished.stopped_reason == "max_tool_rounds"
    assert finished.rounds == 3


async def test_llm_exception_is_converted_to_error_event():
    class BoomLLM(ScriptedLLMClient):
        async def stream_chat(self, messages, tools=()):
            raise RuntimeError("模型炸了")
            yield  # pragma: no cover

    service = AgentService(llm=BoomLLM([]), tools=ToolRegistry(), config=AgentConfig())

    events = await collect(service, "hi")

    errors = [e for e in events if e.type == AgentEventType.ERROR_RAISED]
    assert len(errors) == 1
    assert "模型炸了" in errors[0].message
