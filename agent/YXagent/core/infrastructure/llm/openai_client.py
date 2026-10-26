"""OpenAI 兼容协议的大模型适配器。

使用 ``openai`` SDK 的异步接口实现流式对话，并处理工具调用的增量合并。
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

from core.config import LLMConfig
from core.domain.errors import LLMError
from core.domain.models import Message, ToolCallDelta, ToolSpec
from core.ports.llm import LLMClient


class OpenAICompatibleClient(LLMClient):
    """兼容 OpenAI ``/v1/chat/completions`` 协议的大模型客户端。

    本地推理服务（LM Studio、Ollama 的 OpenAI 兼容端点、vLLM 等）
    都可以直接复用该实现。
    """

    def __init__(self, config: LLMConfig, **client_kwargs: Any) -> None:
        from openai import AsyncOpenAI

        self._config = config
        self._client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key or "not-needed",
            timeout=config.timeout,
            **client_kwargs,
        )

    async def stream_chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] = (),
    ) -> AsyncIterator[Message]:
        """流式对话并产出归一化后的消息增量。"""
        payload_messages = [message.to_wire() for message in messages]
        tool_payload = [spec.to_openai_schema() for spec in tools]

        request_kwargs: dict[str, Any] = {
            "model": self._config.model,
            "messages": payload_messages,
            "stream": True,
        }
        if tool_payload:
            request_kwargs["tools"] = tool_payload
            request_kwargs["tool_choice"] = "auto"

        try:
            stream = await self._client.chat.completions.create(**request_kwargs)
        except Exception as exc:
            raise LLMError(f"调用大模型失败: {exc}") from exc

        try:
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta is None:
                    continue

                content = delta.content or ""
                tool_deltas = _extract_tool_deltas(delta.tool_calls)

                if not content and not tool_deltas:
                    continue

                yield Message(role="assistant", content=content, tool_calls=tuple(tool_deltas))
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"读取流式响应失败: {exc}") from exc

    async def close(self) -> None:
        """关闭底层 HTTP 连接。"""
        await self._client.close()


def _extract_tool_deltas(tool_calls: Any) -> list[ToolCallDelta]:
    """把 SDK 的工具调用增量转换为领域模型。"""
    if not tool_calls:
        return []

    deltas: list[ToolCallDelta] = []
    for call in tool_calls:
        function = getattr(call, "function", None)
        deltas.append(
            ToolCallDelta(
                index=call.index,
                id=getattr(call, "id", None),
                name=getattr(function, "name", None) if function else None,
                arguments=(getattr(function, "arguments", None) or "") if function else "",
            )
        )
    return deltas


__all__ = ["OpenAICompatibleClient"]
