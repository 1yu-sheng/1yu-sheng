"""网络搜索工具。

通过百度千帆「百度搜索」API（v2/ai_search/web_search）获取互联网上的实时信息，
并把搜索结果（摘要、参考来源）整理成一段文本回填给大模型。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from core.domain.models import ToolSpec
from core.infrastructure.tools.base import FunctionTool

DEFAULT_ENDPOINT = "https://qianfan.baidubce.com/v2/ai_search/web_search"
DEFAULT_SEARCH_SOURCE = "baidu_search_v2"

MAX_SUMMARY_CHARS = 4000
MAX_REFERENCES = 10


class SearchWebTool(FunctionTool):
    """使用百度千帆百度搜索 API 搜索互联网。"""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "",
        endpoint: str = DEFAULT_ENDPOINT,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._model = (model or "").strip()
        self._endpoint = endpoint
        self._timeout = timeout
        self._client = client

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="searchWeb",
            description=(
                "搜索互联网获取最新信息。输入自然语言问题或关键词，"
                "返回搜索摘要及参考来源（标题和 URL）。"
                "当需要实时信息、新闻、当前事件或模型知识之外的资料时使用。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要搜索的关键词或自然语言问题",
                    }
                },
                "required": ["query"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return "搜索失败：缺少必填参数 query（搜索关键词或问题）。"

        if not self._api_key:
            return (
                "搜索失败：未配置百度千帆 API Key。请在 config.ini 的 [search] 小节中设置 "
                "baidu_qianfan_api_key，或设置环境变量 YXAGENT_BAIDU_QIANFAN_API_KEY。"
            )

        payload: dict[str, Any] = {
            "messages": [{"role": "user", "content": query.strip()}],
            "search_source": DEFAULT_SEARCH_SOURCE,
        }

        try:
            response = await self._post(payload)
        except httpx.TimeoutException:
            return f"搜索失败：请求百度千帆搜索 API 超时（{self._timeout:g} 秒），请稍后重试。"
        except httpx.HTTPError as exc:
            return f"搜索失败：无法连接百度千帆搜索 API（{exc}）。请检查网络连接后重试。"
        except Exception as exc:  # noqa: BLE001 - 工具异常需转成文本回填给模型
            return f"搜索失败：发起搜索请求时发生异常（{type(exc).__name__}: {exc}）。"

        if response.status_code >= 400:
            return _format_http_error(response)

        try:
            data = response.json()
        except ValueError:
            return "搜索失败：百度千帆搜索 API 返回的内容不是合法 JSON。"

        if not isinstance(data, Mapping):
            return "搜索失败：百度千帆搜索 API 返回的数据格式异常。"

        error = _extract_error(data)
        if error is not None:
            return error

        summary = _extract_summary(data)
        references = _extract_references(data)

        if not summary and not references:
            return f"未找到与「{query.strip()}」相关的搜索结果。"

        return _format_result(query.strip(), summary, references)

    async def _post(self, payload: dict[str, Any]) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._client is not None:
            return await self._client.post(self._endpoint, headers=headers, json=payload)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await client.post(self._endpoint, headers=headers, json=payload)


def _extract_error(data: Mapping[str, Any]) -> str | None:
    """识别响应体中的错误码，返回给模型的错误文本。"""
    code = data.get("code")
    message = data.get("message")

    if code not in (None, "", 0, "0"):
        return _describe_api_error(code, message)

    if message and not data.get("choices") and not data.get("references"):
        return _describe_api_error(None, message)

    return None


def _describe_api_error(code: Any, message: Any) -> str:
    """把 API 错误码/信息翻译成清晰、可操作的中文提示。"""
    text = str(message or "").strip()
    raw_code = str(code) if code not in (None, "") else ""

    if raw_code == "account_overdue" or "overdue" in text.lower():
        return (
            "搜索失败：百度千帆账户已欠费或被冻结（account_overdue），暂时无法调用搜索 API。"
            "请前往百度智能云千帆控制台结清欠费并开通/恢复后付费后重试。"
        )

    if raw_code:
        detail = text or "未知错误"
        return f"搜索失败：百度千帆搜索 API 返回错误（code={raw_code}）：{detail}"
    return f"搜索失败：百度千帆搜索 API 返回错误：{text or '未知错误'}"


def _format_http_error(response: httpx.Response) -> str:
    """把 HTTP 错误响应整理成清晰的错误文本。"""
    code: Any = None
    message: str = ""
    try:
        body = response.json()
        if isinstance(body, Mapping):
            code = body.get("code")
            message = str(body.get("message") or "")
    except ValueError:
        message = response.text.strip()

    if code not in (None, "") or message:
        described = _describe_api_error(code, message or f"HTTP {response.status_code}")
        return described.replace("返回错误", f"返回 HTTP {response.status_code}", 1)
    return f"搜索失败：百度千帆搜索 API 返回 HTTP {response.status_code}。"


def _extract_summary(data: Mapping[str, Any]) -> str:
    """从响应中提取生成摘要。"""
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()

    answer = data.get("answer")
    if isinstance(answer, str) and answer.strip():
        return answer.strip()

    summary = data.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()

    raw = data.get("references")
    if isinstance(raw, list) and raw:
        snippets: list[str] = []
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            content = item.get("content") or item.get("snippet")
            if isinstance(content, str) and content.strip():
                snippets.append(content.strip())
                if len(" ".join(snippets)) >= 200:
                    break
        if snippets:
            text = "\n\n".join(snippets)
            return text.strip()

    return ""


def _extract_references(data: Mapping[str, Any]) -> list[dict[str, str]]:
    """提取网页参考来源的标题与 URL。"""
    raw = data.get("references")
    if not isinstance(raw, list):
        return []

    references: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        url = item.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        title = item.get("title") or item.get("web_anchor")
        references.append(
            {
                "title": title.strip() if isinstance(title, str) and title.strip() else "（无标题）",
                "url": url.strip(),
            }
        )
        if len(references) >= MAX_REFERENCES:
            break
    return references


def _format_result(query: str, summary: str, references: list[dict[str, str]]) -> str:
    """把摘要与参考来源整理成回填给大模型的文本。"""
    if summary:
        trimmed = summary
        if len(trimmed) > MAX_SUMMARY_CHARS:
            trimmed = trimmed[:MAX_SUMMARY_CHARS] + "……"
        summary_text = trimmed
    elif references:
        summary_text = "（API 未返回生成式摘要，以下为搜索结果参考来源。）"
    else:
        summary_text = "（无搜索摘要）"

    lines = [f"搜索关键词：{query}", "", "搜索摘要：", summary_text, "", "参考来源："]
    if references:
        for index, reference in enumerate(references, start=1):
            lines.append(f"{index}. {reference['title']}")
            lines.append(f"   {reference['url']}")
    else:
        lines.append("（无）")
    return "\n".join(lines)


__all__ = ["DEFAULT_ENDPOINT", "DEFAULT_SEARCH_SOURCE", "SearchWebTool"]
