"""TUI 冒烟测试。

使用 Textual 的 ``run_test`` 驱动界面，验证：
* 应用可以正常启动并渲染；
* 提交输入后 core 事件能驱动界面更新；
* 工具调用会渲染成可折叠面板。
"""

from __future__ import annotations

from core.application.agent_service import AgentService
from core.config import AgentConfig
from core.domain.models import ToolSpec
from core.ports.tools import ToolRegistry
from tests.conftest import ScriptedLLMClient, text_chunk, tool_chunk
from tui.app import YXAgentApp
from tui.widgets import ChatLog, ToolCallView, UserMessage


class EchoTool:
    """测试用的回显工具。"""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(name="echo", description="回显输入", parameters={})

    async def execute(self, arguments: dict) -> str:
        return f"echo:{arguments.get('value')}"


def build_app(client: ScriptedLLMClient, tools: ToolRegistry | None = None) -> YXAgentApp:
    service = AgentService(
        llm=client,
        tools=tools or ToolRegistry(),
        config=AgentConfig(),
    )
    return YXAgentApp(service, model="test-model", workspace="C:/tmp")


async def test_app_starts_and_shows_welcome():
    app = build_app(ScriptedLLMClient([]))
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.title == "YXAgent"
        assert app.screen.query_one("#prompt-input") is not None


async def test_submitting_input_renders_user_message():
    client = ScriptedLLMClient([[text_chunk("你好")]])
    app = build_app(client)

    async with app.run_test() as pilot:
        await pilot.pause()
        prompt = app.screen.query_one("#prompt-input")
        prompt.text = "hi"
        await pilot.press("enter")
        for _ in range(6):
            await pilot.pause(0.05)

        users = app.screen.query(UserMessage)
        assert len(users) == 1
        assert "hi" in users.first()._text


async def test_tool_call_renders_collapsible_panel():
    client = ScriptedLLMClient(
        [
            [tool_chunk(0, "call_1", "echo", '{"value": "x"}')],
            [text_chunk("done")],
        ]
    )
    app = build_app(client, ToolRegistry([EchoTool()]))

    async with app.run_test() as pilot:
        await pilot.pause()
        prompt = app.screen.query_one("#prompt-input")
        prompt.text = "调用"
        await pilot.press("enter")
        for _ in range(12):
            await pilot.pause(0.05)

        views = app.screen.query(ToolCallView)
        assert len(views) == 1
        assert views.first().tool_name == "echo"
        assert views.first().collapsed is True


async def test_tool_panel_appears_before_final_reply():
    """工具面板应排在助手最终回复之前。"""
    client = ScriptedLLMClient(
        [
            [tool_chunk(0, "call_1", "echo", '{"value": "x"}')],
            [text_chunk("done")],
        ]
    )
    app = build_app(client, ToolRegistry([EchoTool()]))

    async with app.run_test() as pilot:
        await pilot.pause()
        prompt = app.screen.query_one("#prompt-input")
        prompt.text = "调用"
        await pilot.press("enter")
        for _ in range(12):
            await pilot.pause(0.05)

        children = list(app.screen.query_one("#chat-log", ChatLog).children)
        kinds = [type(child).__name__ for child in children]
        assert kinds.index("ToolCallView") < kinds.index("AssistantMessage")


async def test_clear_history_action_resets_session():
    client = ScriptedLLMClient([[text_chunk("你好")]])
    app = build_app(client)

    async with app.run_test() as pilot:
        await pilot.pause()
        prompt = app.screen.query_one("#prompt-input")
        prompt.text = "hi"
        await pilot.press("enter")
        for _ in range(6):
            await pilot.pause(0.05)

        assert app.screen._service.session.messages

        await app.screen.action_clear_history()
        await pilot.pause()

        assert not app.screen._service.session.messages
