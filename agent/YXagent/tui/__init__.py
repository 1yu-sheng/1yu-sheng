"""Textual 终端用户界面（TUI）。

分层约定：

``tui.app``        —— 应用外壳（组合根），负责装配 core 服务与界面；
``tui.screens``    —— 界面（Screen），负责事件 → 视图的翻译；
``tui.widgets``    —— 可复用的界面控件；
``tui.presenter``  —— core 事件到界面动作的解耦层。

TUI 层只依赖 :mod:`core` 的公开接口，不直接依赖任何基础设施实现。
"""

from tui.app import YXAgentApp, run

__all__ = ["YXAgentApp", "run"]
