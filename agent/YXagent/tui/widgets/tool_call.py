"""工具调用展示控件。"""

from __future__ import annotations

import json

from rich.text import Text
from textual.widgets import Collapsible, Static


class ToolCallView(Collapsible):
    """展示一次工具调用及其结果。

    默认折叠，用户可展开查看参数与返回值。
    """

    DEFAULT_CSS = """
    ToolCallView {
        height: auto;
        margin: 0 0 1 0;
        padding: 0 1;
        border-top: none;
        border-left: thick $warning;
        background: $panel;
    }
    ToolCallView .tool-status {
        color: $warning;
        text-style: italic;
    }
    ToolCallView .tool-status.is-error {
        color: $error;
        text-style: bold;
    }
    ToolCallView .tool-result {
        color: $text-muted;
    }
    """

    def __init__(self, name: str, arguments: str = "{}") -> None:
        self._tool_name = name
        self._arguments = arguments
        self._status = Static("", classes="tool-status")
        self._result = Static("", classes="tool-result")
        self._done = False
        self._ok = True
        super().__init__(self._status, self._result, title=f"工具 {name}", collapsed=True)

    @property
    def tool_name(self) -> str:
        """被调用的工具名称。"""
        return self._tool_name

    def on_mount(self) -> None:
        """挂载后渲染当前状态。"""
        self._render_status()

    def set_result(self, result: str, ok: bool = True) -> None:
        """更新工具执行结果。"""
        self._done = True
        self._ok = ok
        self._result.update(self._format_result(result))
        self._render_status()

    def _render_status(self) -> None:
        """根据执行状态渲染提示文本。"""
        if not self._done:
            text = "执行中…"
            classes = "tool-status"
        elif self._ok:
            text = "执行完成"
            classes = "tool-status"
        else:
            text = "执行失败"
            classes = "tool-status is-error"
        self._status.set_classes(classes)
        self._status.update(Text(text))

    def _format_result(self, result: str) -> Text:
        """格式化参数与结果文本。"""
        text = Text()
        text.append("参数: ", style="dim")
        text.append(self._format_arguments())
        text.append("\n结果:\n")
        text.append(result)
        return text

    def _format_arguments(self) -> str:
        """把参数串格式化为易读的多行 JSON。"""
        try:
            parsed = json.loads(self._arguments or "{}")
        except (json.JSONDecodeError, TypeError):
            return self._arguments or "{}"
        return json.dumps(parsed, ensure_ascii=False, indent=2)


__all__ = ["ToolCallView"]
