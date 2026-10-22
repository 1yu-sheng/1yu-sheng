"""core 层的测试夹具。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.domain.models import Message, ToolCallDelta
from core.ports.llm import LLMClient


class ScriptedLLMClient(LLMClient):
    """按预置脚本返回流式响应的假客户端。"""

    def __init__(self, scripts: list[list[Message]]) -> None:
        self._scripts = list(scripts)
        self.closed = False
        self.calls: list[list[Message]] = []

    async def stream_chat(self, messages, tools=()):
        self.calls.append(list(messages))
        if not self._scripts:
            return
        script = self._scripts.pop(0)
        for chunk in script:
            yield chunk

    async def close(self) -> None:
        self.closed = True


def text_chunk(text: str) -> Message:
    """构造纯文本增量。"""
    return Message(role="assistant", content=text)


def tool_chunk(index: int, call_id: str, name: str, arguments: str) -> Message:
    """构造工具调用增量。"""
    return Message(
        role="assistant",
        content="",
        tool_calls=(ToolCallDelta(index=index, id=call_id, name=name, arguments=arguments),),
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """提供一个隔离的工作目录。"""
    return tmp_path
