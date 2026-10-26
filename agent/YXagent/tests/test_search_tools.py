"""网络搜索工具测试。"""

from __future__ import annotations

import httpx
import pytest

from core.config import load_config
from core.infrastructure.tools.web_search import SearchWebTool


def _build_tool(handler, *, api_key: str = "test-key", timeout: float = 5.0) -> SearchWebTool:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return SearchWebTool(api_key, timeout=timeout, client=client)


def test_spec_declares_search_web():
    tool = SearchWebTool("key")

    assert tool.spec.name == "searchWeb"
    assert tool.spec.parameters["required"] == ["query"]


@pytest.mark.asyncio
async def test_missing_api_key_returns_clear_error():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - 不应被调用
        calls.append(request)
        return httpx.Response(200, json={})

    tool = _build_tool(handler, api_key="")

    result = await tool.run({"query": "今天天气"})

    assert "未配置" in result
    assert "baidu_qianfan_api_key" in result
    assert calls == []


@pytest.mark.asyncio
async def test_missing_query_returns_error():
    tool = SearchWebTool("key")

    result = await tool.run({})

    assert "query" in result


@pytest.mark.asyncio
async def test_success_formats_summary_and_references():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "这是搜索摘要。"}}],
                "references": [
                    {"title": "来源一", "url": "https://example.com/1"},
                    {"title": "来源二", "url": "https://example.com/2"},
                ],
            },
        )

    tool = _build_tool(handler)

    result = await tool.run({"query": "测试问题"})

    assert "这是搜索摘要。" in result
    assert "来源一" in result
    assert "https://example.com/1" in result
    assert "来源二" in result
    assert "https://example.com/2" in result


@pytest.mark.asyncio
async def test_api_error_body_returns_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": "InvalidArgument", "message": "参数错误"})

    tool = _build_tool(handler)

    result = await tool.run({"query": "问题"})

    assert "搜索失败" in result
    assert "InvalidArgument" in result
    assert "参数错误" in result


@pytest.mark.asyncio
async def test_account_overdue_returns_actionable_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": "account_overdue", "message": "Access denied due to overdue account"},
        )

    tool = _build_tool(handler)

    result = await tool.run({"query": "问题"})

    assert "欠费" in result
    assert "account_overdue" in result


@pytest.mark.asyncio
async def test_http_error_status_returns_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"code": "Unauthorized", "message": "鉴权失败"})

    tool = _build_tool(handler)

    result = await tool.run({"query": "问题"})

    assert "401" in result
    assert "鉴权失败" in result


@pytest.mark.asyncio
async def test_network_error_returns_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    tool = _build_tool(handler)

    result = await tool.run({"query": "问题"})

    assert "搜索失败" in result
    assert "网络" in result or "连接" in result


@pytest.mark.asyncio
async def test_timeout_returns_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    tool = _build_tool(handler)

    result = await tool.run({"query": "问题"})

    assert "超时" in result


@pytest.mark.asyncio
async def test_empty_result_returns_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [], "references": []})

    tool = _build_tool(handler)

    result = await tool.run({"query": "不存在的关键词"})

    assert "未找到" in result


def test_load_config_reads_search_section(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "[llm]\nmodel=\"m\"\n\n[search]\n"
        "baidu_qianfan_api_key=\"qianfan-key\"\nmodel=\"ernie-4.5-turbo-32k\"\ntimeout=15\n",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.search.baidu_qianfan_api_key == "qianfan-key"
    assert config.search.model == "ernie-4.5-turbo-32k"
    assert config.search.timeout == 15.0
