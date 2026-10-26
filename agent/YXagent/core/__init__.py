"""core 层门面。

对外只暴露稳定接口，内部按 domain / ports / application / infrastructure 分层。
前端（tui / web / desktop / mobile）**只应依赖本模块导出的内容**，
不要直接引用 ``core.*`` 的内部子模块，以保证后续重构的兼容性。
"""

from core.application.agent_service import AgentService, Session
from core.bootstrap import create_agent_service
from core.config import AgentConfig, AppConfig, LLMConfig, SearchConfig, load_config
from core.domain.errors import (
    ConfigurationError,
    LLMError,
    ToolArgumentError,
    ToolExecutionError,
    ToolNotFoundError,
    YXAgentError,
)
from core.domain.events import (
    AgentEvent,
    AgentEventType,
    AssistantCompleted,
    AssistantDelta,
    ErrorRaised,
    ToolCallFinished,
    ToolCallStarted,
    TurnFinished,
    TurnStarted,
)
from core.domain.models import Message, Role, ToolCall, ToolCallDelta, ToolResult, ToolSpec
from core.infrastructure.llm.openai_client import OpenAICompatibleClient
from core.infrastructure.tools.builtin import build_default_registry
from core.infrastructure.tools.filesystem_service import FileSystemService
from core.ports.llm import LLMClient
from core.ports.tools import Tool, ToolRegistry

__all__ = [
    "AgentConfig",
    "AgentEvent",
    "AgentEventType",
    "AgentService",
    "AppConfig",
    "AssistantCompleted",
    "AssistantDelta",
    "ConfigurationError",
    "ErrorRaised",
    "FileSystemService",
    "LLMClient",
    "LLMConfig",
    "LLMError",
    "Message",
    "OpenAICompatibleClient",
    "Role",
    "SearchConfig",
    "Session",
    "Tool",
    "ToolArgumentError",
    "ToolCall",
    "ToolCallDelta",
    "ToolCallFinished",
    "ToolCallStarted",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolRegistry",
    "ToolResult",
    "ToolSpec",
    "TurnFinished",
    "TurnStarted",
    "YXAgentError",
    "build_default_registry",
    "create_agent_service",
    "load_config",
]
