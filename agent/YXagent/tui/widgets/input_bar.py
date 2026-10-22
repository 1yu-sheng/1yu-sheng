"""用户输入区。"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Static, TextArea


class PromptInput(TextArea):
    """多行输入框。

    * ``Enter`` —— 提交；
    * ``Shift+Enter`` —— 换行。
    """

    DEFAULT_CSS = """
    PromptInput {
        width: 1fr;
        height: auto;
        min-height: 3;
        max-height: 12;
        border: round $accent;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("shift+enter", "insert_newline", "换行", show=False),
    ]

    class Submitted(Message):
        """用户提交了一条输入。"""

        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def __init__(self) -> None:
        super().__init__(
            placeholder="输入你的问题……（Enter 发送，Shift+Enter 换行）",
            soft_wrap=True,
            show_line_numbers=False,
            id="prompt-input",
        )

    async def _on_key(self, event) -> None:  # type: ignore[override]
        """拦截 Enter 用于提交，其余按键交回默认处理。"""
        if event.key == "enter":
            event.stop()
            event.prevent_default()
            await self.action_submit()
            return
        await super()._on_key(event)

    async def action_submit(self) -> None:
        """提交当前内容。"""
        value = self.text.strip()
        if not value:
            return
        self.text = ""
        self.post_message(self.Submitted(value))

    def action_insert_newline(self) -> None:
        """插入换行符。"""
        self.insert("\n")


class InputBar(Horizontal):
    """输入区容器：快捷键提示 + 输入框。"""

    DEFAULT_CSS = """
    InputBar {
        height: auto;
        width: 1fr;
        padding: 0 2 1 2;
    }
    InputBar .hint {
        width: 1fr;
        height: 0;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", classes="hint")
        yield PromptInput()


__all__ = ["InputBar", "PromptInput"]
