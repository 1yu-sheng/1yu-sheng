"""领域层异常定义。

所有异常继承自 :class:`YXAgentError`，方便上层统一捕获与转换成 UI 事件。
"""

from __future__ import annotations


class YXAgentError(Exception):
    """框架内所有异常的基类。"""


class ConfigurationError(YXAgentError):
    """配置缺失或非法。"""


class LLMError(YXAgentError):
    """大模型调用失败。"""


class ToolNotFoundError(YXAgentError):
    """请求的工具不存在。"""


class ToolExecutionError(YXAgentError):
    """工具执行失败。"""


class ToolArgumentError(YXAgentError):
    """工具参数非法。"""
