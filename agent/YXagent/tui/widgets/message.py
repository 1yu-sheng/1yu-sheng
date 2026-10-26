"""对话消息展示控件。"""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Markdown, Static


class UserMessage(Vertical):
    """用户消息气泡。"""

    DEFAULT_CSS = """
    UserMessage {
        height: auto;
        margin: 0 0 1 0;
        padding: 0 1;
        border-left: thick $accent;
    }
    UserMessage .role-label {
        color: $accent;
        text-style: bold;
    }
    """

    def __init__(self, text: str) -> None:
        super().__init__(classes="user-message")
        self._text = text

    def compose(self) -> ComposeResult:
        yield Static(Text("你", style="bold"), classes="role-label")
        yield Static(self._text, classes="message-body")


class AssistantMessage(Vertical):
    """助手消息气泡（Markdown 渲染，支持流式追加）。"""

    DEFAULT_CSS = """
    AssistantMessage {
        height: auto;
        margin: 0 0 1 0;
        padding: 0 1;
        border-left: thick $success;
    }
    AssistantMessage .role-label {
        color: $success;
        text-style: bold;
    }
    """

    def __init__(self) -> None:
        super().__init__(classes="assistant-message")
        self._markdown = Markdown("")

    def compose(self) -> ComposeResult:
        yield Static(Text("YXAgent", style="bold"), classes="role-label")
        yield self._markdown

    async def append_text(self, text: str) -> None:
        """追加流式文本。"""
        if not text:
            return
        await self._markdown.append(text)

    async def finalize(self, text: str) -> None:
        """结束流式输出并渲染最终内容。"""
        await self._markdown.update(text)

    @property
    def markdown_widget(self) -> Markdown:
        return self._markdown


class SystemMessage(Vertical):
    """系统提示 / 错误信息。"""

    DEFAULT_CSS = """
    SystemMessage {
        height: auto;
        margin: 0 0 1 0;
        padding: 0 1;
        border-left: thick $warning;
        color: $text-muted;
    }
    """

    def __init__(self, text: str, variant: str = "info") -> None:
        super().__init__(classes=f"system-message {variant}")
        self._text = text

    def compose(self) -> ComposeResult:
        yield Static(self._text)


__all__ = ["AssistantMessage", "SystemMessage", "UserMessage"]
