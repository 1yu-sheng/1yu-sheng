"""主对话界面。"""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header

from core import AgentService, ErrorRaised, ToolCallFinished, ToolCallStarted
from tui.presenter import AgentPresenter
from tui.widgets import (
    AssistantMessage,
    ChatLog,
    InputBar,
    PromptInput,
    StatusBar,
    ToolCallView,
)


class ChatScreen(Screen[None]):
    """YXAgent 的主界面。

    职责边界：

    * 本模块只负责"事件 → 界面"的翻译；
    * 所有业务逻辑（工具调用、模型交互）都在 :mod:`core` 中完成。

    因此新增 Web / Desktop 前端时，只需复用 core 的事件流并重写各自的界面层。
    """

    BINDINGS = [
        Binding("ctrl+l", "clear_history", "清空历史"),
        Binding("ctrl+t", "show_tools", "查看工具"),
        Binding("ctrl+q", "quit", "退出"),
    ]

    def __init__(self, service: AgentService, model: str, workspace: str) -> None:
        super().__init__()
        self._service = service
        self._model = model
        self._workspace = workspace
        self._presenter = AgentPresenter()
        self._assistant_widget: AssistantMessage | None = None
        self._tool_views: dict[str, ToolCallView] = {}
        self._busy = False

    # ------------------------------------------------------------------
    # 布局
    # ------------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield StatusBar(id="status-bar")
        yield ChatLog(id="chat-log")
        yield InputBar()
        yield Footer()

    async def on_mount(self) -> None:
        """界面挂载后的初始化。"""
        status = self.query_one("#status-bar", StatusBar)
        status.update_model(self._model)
        status.update_workspace(self._workspace)
        status.update_state("就绪")

        self._bind_presenter()
        await self.query_one("#chat-log", ChatLog).add_system_message(
            "欢迎使用 YXAgent。输入问题后按 Enter 发送，Shift+Enter 换行。"
        )
        self.query_one(PromptInput).focus()

    # ------------------------------------------------------------------
    # 事件绑定
    # ------------------------------------------------------------------
    def _bind_presenter(self) -> None:
        """把 core 事件订阅到界面更新动作。"""
        presenter = self._presenter

        async def on_turn_started(event) -> None:
            self._busy = True
            self._set_state("思考中…", busy=True)
            await self.query_one("#chat-log", ChatLog).add_user_message(event.user_input)
            # 助手气泡延迟创建，保证工具面板出现在最终回复之前
            self._assistant_widget = None

        async def on_assistant_delta(event) -> None:
            if self._assistant_widget is None:
                self._assistant_widget = await self.query_one(
                    "#chat-log", ChatLog
                ).add_assistant_message()
            await self._assistant_widget.append_text(event.text)
            self.query_one("#chat-log", ChatLog).scroll_end(animate=False)

        async def on_assistant_completed(event) -> None:
            if self._assistant_widget is None:
                # 模型没有产生任何文本（例如只调用了工具）
                self._assistant_widget = await self.query_one(
                    "#chat-log", ChatLog
                ).add_assistant_message()
            await self._assistant_widget.finalize(event.text)
            self._assistant_widget = None

        async def on_tool_started(event: ToolCallStarted) -> None:
            view = ToolCallView(event.name, event.arguments)
            self._tool_views[event.call_id] = view
            await self.query_one("#chat-log", ChatLog).mount(view)
            self.query_one("#chat-log", ChatLog).scroll_end(animate=False)

        def on_tool_finished(event: ToolCallFinished) -> None:
            view = self._tool_views.pop(event.call_id, None)
            if view is not None:
                view.set_result(event.result, event.ok)
            # 工具调用后的模型回复应另起一个气泡
            self._assistant_widget = None
            self.query_one("#chat-log", ChatLog).scroll_end(animate=False)

        def on_turn_finished(event) -> None:
            self._busy = False
            if event.stopped_reason == "max_tool_rounds":
                self._set_state("已达工具轮次上限")
            else:
                self._set_state("就绪")

        async def on_error(event: ErrorRaised) -> None:
            self._busy = False
            self._set_state("错误")
            await self._append_error(event.message)

        presenter.on_turn_started(on_turn_started)
        presenter.on_assistant_delta(on_assistant_delta)
        presenter.on_assistant_completed(on_assistant_completed)
        presenter.on_tool_started(on_tool_started)
        presenter.on_tool_finished(on_tool_finished)
        presenter.on_turn_finished(on_turn_finished)
        presenter.on_error(on_error)

    async def _append_error(self, message: str) -> None:
        await self.query_one("#chat-log", ChatLog).add_system_message(f"错误: {message}", "error")

    def _set_state(self, state: str, busy: bool = False) -> None:
        self.query_one("#status-bar", StatusBar).update_state(state, busy=busy)

    # ------------------------------------------------------------------
    # 交互
    # ------------------------------------------------------------------
    @work(exclusive=True)
    async def _run_turn(self, user_input: str) -> None:
        """消费 core 的事件流并驱动界面更新。"""
        try:
            async for event in self._service.run_turn(user_input):
                await self._presenter.dispatch(event)
        except Exception as exc:  # noqa: BLE001 - 兜底，避免 worker 静默死亡
            await self._presenter.dispatch(ErrorRaised(message=str(exc)))

    async def on_prompt_input_submitted(self, event: PromptInput.Submitted) -> None:
        """用户提交输入。"""
        if self._busy:
            return
        self._run_turn(event.value)

    # ------------------------------------------------------------------
    # 动作
    # ------------------------------------------------------------------
    async def action_clear_history(self) -> None:
        """清空对话历史。"""
        self._service.reset()
        await self.query_one("#chat-log", ChatLog).clear_history()
        self._assistant_widget = None
        self._tool_views.clear()
        self._set_state("就绪")

    async def action_show_tools(self) -> None:
        """列出当前可用的工具。"""
        specs = self._service.tool_specs()
        lines = [f"- {spec.name}: {spec.description}" for spec in specs]
        await self.query_one("#chat-log", ChatLog).add_system_message(
            "可用工具:\n" + "\n".join(lines)
        )


__all__ = ["ChatScreen"]
