"""基础设施层：与具体技术栈打交道的适配器。"""

from core.infrastructure.llm.openai_client import OpenAICompatibleClient
from core.infrastructure.tools.builtin import build_default_registry

__all__ = ["OpenAICompatibleClient", "build_default_registry"]
