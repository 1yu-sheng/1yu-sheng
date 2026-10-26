"""对话历史容器。"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from tui.widgets.message import AssistantMessage, SystemMessage, UserMessage


class ChatLog(VerticalScroll):
    """滚动显示整个对话历史。"""

    DEFAULT_CSS = """
    ChatLog {
        height: 1fr;
        width: 1fr;
        padding: 1 2;
        scrollbar-size-vertical: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="welcome-banner")

    async def add_user_message(self, text: str) -> UserMessage:
        """追加一条用户消息。"""
        widget = UserMessage(text)
        await self.mount(widget)
        self.scroll_end(animate=False)
        return widget

    async def add_assistant_message(self) -> AssistantMessage:
        """追加一条助手消息（返回后可持续流式追加）。"""
        widget = AssistantMessage()
        await self.mount(widget)
        self.scroll_end(animate=False)
        return widget

    async def add_system_message(self, text: str, variant: str = "info") -> SystemMessage:
        """追加一条系统/提示消息。"""
        widget = SystemMessage(text, variant)
        await self.mount(widget)
        self.scroll_end(animate=False)
        return widget

    async def clear_history(self) -> None:
        """清空历史，保留欢迎横幅。"""
        banner = self.query_one("#welcome-banner", Static)
        await self.remove_children()
        await self.mount(banner)


__all__ = ["ChatLog"]
