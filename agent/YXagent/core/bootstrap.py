"""组合根（Composition Root）。

集中装配 core 的所有依赖，任何前端（tui / web / desktop / mobile）
都通过本模块创建 :class:`~core.application.agent_service.AgentService`，
从而保证不同前端的行为完全一致。
"""

from __future__ import annotations

import os

from core.application.agent_service import AgentService
from core.config import AppConfig, load_config
from core.infrastructure.llm.openai_client import OpenAICompatibleClient
from core.infrastructure.tools.builtin import build_default_registry
from core.ports.llm import LLMClient
from core.ports.tools import ToolRegistry


def create_agent_service(
    config: AppConfig | None = None,
    *,
    config_path: str | os.PathLike[str] | None = None,
    llm: LLMClient | None = None,
    tools: ToolRegistry | None = None,
) -> AgentService:
    """创建配置完毕的 Agent 服务。

    Args:
        config: 显式配置；为 ``None`` 时从配置文件/环境变量加载。
        config_path: 配置文件路径（仅在 ``config`` 为 ``None`` 时生效）。
        llm: 自定义大模型客户端（便于测试或替换供应商）。
        tools: 自定义工具注册表（便于扩展或裁剪工具集）。

    Returns:
        可直接驱动的事件流式 Agent 服务。
    """
    resolved = config or load_config(config_path)
    client = llm or OpenAICompatibleClient(resolved.llm)
    registry = tools or build_default_registry(resolved)
    return AgentService(llm=client, tools=registry, config=resolved.agent)


__all__ = ["create_agent_service"]
