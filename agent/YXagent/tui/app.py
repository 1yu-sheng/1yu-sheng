"""TUI 应用外壳（组合根）。

只做三件事：

1. 加载配置并创建 core 的 :class:`~core.application.agent_service.AgentService`；
2. 创建界面并进入主循环；
3. 退出时释放模型客户端资源。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from textual.app import App

from core import AgentService, ConfigurationError, create_agent_service, load_config
from tui.screens.chat_screen import ChatScreen


class YXAgentApp(App):
    """YXAgent 的 Textual 应用。"""

    TITLE = "YXAgent"
    SUB_TITLE = "基于 Textual 的终端智能体"

    CSS_PATH = "styles.tcss"

    def __init__(self, service: AgentService, model: str, workspace: str) -> None:
        super().__init__()
        self._service = service
        self._model = model
        self._workspace = workspace

    def on_mount(self) -> None:
        """挂载主界面。"""
        self.push_screen(ChatScreen(self._service, self._model, self._workspace))

    async def on_unmount(self) -> None:
        """退出时释放模型客户端。"""
        await self._service.aclose()


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="yxagent",
        description="YXAgent —— 基于 Textual 的终端智能体",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        help="配置文件路径（默认在当前目录或项目根目录查找 config.ini）",
    )
    parser.add_argument(
        "-w",
        "--workspace",
        default=None,
        help="工具的工作目录（默认为当前目录）",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    """启动 TUI。

    Args:
        argv: 命令行参数，默认取 ``sys.argv[1:]``。

    Returns:
        进程退出码。
    """
    args = build_parser().parse_args(argv)

    try:
        config = load_config(args.config, workspace=args.workspace)
    except ConfigurationError as exc:
        print(f"配置错误: {exc}", file=sys.stderr)
        return 2

    service = create_agent_service(config)
    app = YXAgentApp(service, model=config.llm.model, workspace=str(config.workspace))
    app.run()
    return 0


def main() -> None:
    """命令行入口。"""
    raise SystemExit(run())


if __name__ == "__main__":
    main()
