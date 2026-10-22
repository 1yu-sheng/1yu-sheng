"""配置模块。

配置来源优先级（从高到低）：

1. 环境变量 ``YXAGENT_BASE_URL`` / ``YXAGENT_API_KEY`` / ``YXAGENT_MODEL``；
2. ``config.ini`` 文件（``[llm]`` 段，也兼容无段头的旧格式）；
3. 内置默认值。

所有前端共用这一份配置，保证 core 与 UI 行为一致。
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field
from pathlib import Path

from core.domain.errors import ConfigurationError

DEFAULT_CONFIG_FILENAME = "config.ini"

ENV_BASE_URL = "YXAGENT_BASE_URL"
ENV_API_KEY = "YXAGENT_API_KEY"
ENV_MODEL = "YXAGENT_MODEL"


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """大模型连接配置。"""

    base_url: str = "http://127.0.0.1:1234/v1"
    api_key: str = ""
    model: str = ""
    timeout: float = 120.0

    def __post_init__(self) -> None:
        if not self.model:
            raise ConfigurationError("未配置模型名称（model），请设置 config.ini 或环境变量 YXAGENT_MODEL")


@dataclass(frozen=True, slots=True)
class AgentConfig:
    """Agent 运行参数。"""

    max_tool_rounds: int = 8
    """单轮对话内允许的最大工具调用轮次。"""

    max_read_chars: int = 8000
    """单次读取文件的最大字符数。"""

    system_prompt: str = ""
    """系统提示词。"""

    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class AppConfig:
    """应用整体配置。"""

    llm: LLMConfig
    agent: AgentConfig = field(default_factory=AgentConfig)
    workspace: Path = field(default_factory=Path.cwd)
    """工具默认工作目录。"""


def _find_config_file(explicit: str | os.PathLike[str] | None = None) -> Path | None:
    """按优先级定位配置文件。"""
    if explicit is not None:
        path = Path(explicit)
        if not path.is_file():
            raise ConfigurationError(f"配置文件不存在: {path}")
        return path

    candidates = [
        Path.cwd() / DEFAULT_CONFIG_FILENAME,
        Path(__file__).resolve().parents[2] / DEFAULT_CONFIG_FILENAME,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _read_config_file(path: Path) -> configparser.ConfigParser:
    """读取配置文件，兼容原始无段头格式。"""
    parser = configparser.ConfigParser()
    text = path.read_text(encoding="utf-8")
    try:
        parser.read_string(text)
    except configparser.MissingSectionHeaderError:
        parser.read_string("[llm]\n" + text)
    return parser


def load_config(
    config_path: str | os.PathLike[str] | None = None,
    *,
    workspace: str | os.PathLike[str] | None = None,
) -> AppConfig:
    """加载配置。

    Args:
        config_path: 显式指定的配置文件路径。
        workspace: 工具工作目录，默认为当前工作目录。

    Raises:
        ConfigurationError: 配置缺失或非法。
    """
    parser = configparser.ConfigParser()
    path = _find_config_file(config_path)
    if path is not None:
        parser = _read_config_file(path)

    def pick(key: str, env: str, default: str = "") -> str:
        env_value = os.environ.get(env)
        if env_value:
            return env_value
        if parser.has_option("llm", key):
            return parser.get("llm", key).strip().strip('"').strip("'")
        return default

    base_url = pick("base_url", ENV_BASE_URL, "http://127.0.0.1:1234/v1")
    api_key = pick("api_key", ENV_API_KEY)
    model = pick("model", ENV_MODEL)

    if not model:
        raise ConfigurationError(
            "未找到模型配置。请在 config.ini 中提供 [llm] model，"
            "或设置环境变量 YXAGENT_MODEL。"
        )

    llm = LLMConfig(base_url=base_url, api_key=api_key, model=model)
    agent = AgentConfig(
        max_tool_rounds=int(parser.get("agent", "max_tool_rounds", fallback="8")),
        max_read_chars=int(parser.get("agent", "max_read_chars", fallback="8000")),
        system_prompt=parser.get("agent", "system_prompt", fallback="").strip(),
        temperature=_optional_float(parser.get("llm", "temperature", fallback="")),
        max_tokens=_optional_int(parser.get("llm", "max_tokens", fallback="")),
    )
    workspace_path = Path(workspace) if workspace else Path.cwd()
    return AppConfig(llm=llm, agent=agent, workspace=workspace_path.resolve())


def _optional_float(raw: str) -> float | None:
    raw = raw.strip().strip('"').strip("'")
    return float(raw) if raw else None


def _optional_int(raw: str) -> int | None:
    raw = raw.strip().strip('"').strip("'")
    return int(raw) if raw else None


__all__ = [
    "DEFAULT_CONFIG_FILENAME",
    "AgentConfig",
    "AppConfig",
    "LLMConfig",
    "load_config",
]
