"""领域层：纯数据模型与事件契约，不依赖任何第三方框架。"""

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
from core.domain.models import (
    Message,
    Role,
    ToolCall,
    ToolCallDelta,
    ToolResult,
    ToolSpec,
)

__all__ = [
    "AgentEvent",
    "AgentEventType",
    "AssistantCompleted",
    "AssistantDelta",
    "ConfigurationError",
    "ErrorRaised",
    "LLMError",
    "Message",
    "Role",
    "ToolArgumentError",
    "ToolCall",
    "ToolCallDelta",
    "ToolCallFinished",
    "ToolCallStarted",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolResult",
    "ToolSpec",
    "TurnFinished",
    "TurnStarted",
    "YXAgentError",
]
