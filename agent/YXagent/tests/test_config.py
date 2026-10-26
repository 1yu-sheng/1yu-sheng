"""配置加载测试。"""

from __future__ import annotations

import pytest

from core.config import load_config
from core.domain.errors import ConfigurationError


def test_load_config_from_ini(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        '[llm]\nbase_url = "http://example.com/v1"\napi_key = "secret"\nmodel = "demo-model"\n',
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.llm.base_url == "http://example.com/v1"
    assert config.llm.api_key == "secret"
    assert config.llm.model == "demo-model"
    assert config.agent.max_tool_rounds == 8


def test_load_config_supports_legacy_headerless_format(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text('base_url="http://legacy/v1"\nmodel="legacy-model"\n', encoding="utf-8")

    config = load_config(config_file)

    assert config.llm.model == "legacy-model"
    assert config.llm.base_url == "http://legacy/v1"


def test_env_overrides_ini(tmp_path, monkeypatch):
    config_file = tmp_path / "config.ini"
    config_file.write_text('[llm]\nmodel="from-file"\n', encoding="utf-8")

    monkeypatch.setenv("YXAGENT_MODEL", "from-env")
    config = load_config(config_file)

    assert config.llm.model == "from-env"


def test_missing_model_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("YXAGENT_MODEL", raising=False)
    config_file = tmp_path / "config.ini"
    config_file.write_text('[llm]\nbase_url="http://x/v1"\n', encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_config(config_file)


def test_explicit_missing_file_raises(tmp_path):
    with pytest.raises(ConfigurationError):
        load_config(tmp_path / "does-not-exist.ini")


def test_agent_section_overrides_defaults(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        '[llm]\nmodel="m"\n\n[agent]\nmax_tool_rounds=3\nmax_read_chars=100\n',
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.agent.max_tool_rounds == 3
    assert config.agent.max_read_chars == 100
