"""顶部状态栏。"""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static


class StatusBar(Horizontal):
    """显示模型名称、工作目录与运行状态。"""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        width: 1fr;
        background: $panel;
        color: $text-muted;
        padding: 0 2;
    }
    StatusBar .status-model {
        width: auto;
        color: $accent;
    }
    StatusBar .status-workspace {
        width: 1fr;
    }
    StatusBar .status-state {
        width: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="status-model", classes="status-model")
        yield Static("", id="status-workspace", classes="status-workspace")
        yield Static("", id="status-state", classes="status-state")

    def update_model(self, model: str) -> None:
        """更新模型名称。"""
        self.query_one("#status-model", Static).update(Text(model, style="bold"))

    def update_workspace(self, workspace: str) -> None:
        """更新工作目录。"""
        self.query_one("#status-workspace", Static).update(f"工作目录: {workspace}")

    def update_state(self, state: str, busy: bool = False) -> None:
        """更新运行状态。"""
        style = "bold green" if not busy else "bold yellow"
        self.query_one("#status-state", Static).update(Text(state, style=style))


__all__ = ["StatusBar"]
