"""大模型端口（Port）。

定义 core 层对"大模型"的抽象，使 core 不依赖任何具体的模型 SDK。
更换模型供应商（OpenAI / Anthropic / Ollama / 本地推理）时，
只需新增一个 :class:`LLMClient` 实现即可，上层应用服务无需改动。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence

from core.domain.models import Message, ToolCallDelta, ToolSpec


class LLMClient(ABC):
    """大模型客户端抽象。"""

    @abstractmethod
    async def stream_chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] = (),
    ) -> AsyncIterator[Message]:
        """流式对话。

        Args:
            messages: 上下文消息列表。
            tools: 可用工具声明；为空表示不做工具调用。

        Yields:
            包含 ``content`` 的 :class:`Message`（role=assistant），以及可选的
            ``tool_calls`` 增量。
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """释放底层连接资源。"""
        raise NotImplementedError


__all__ = ["LLMClient", "ToolCallDelta"]
