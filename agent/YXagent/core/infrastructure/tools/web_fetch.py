"""网页内容抓取工具。

通过本地 curl 获取网页 HTML，再使用 trafilatura 提取正文并转换为 Markdown。
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from typing import Any

import trafilatura

from core.domain.models import ToolSpec
from core.infrastructure.tools.base import FunctionTool


class FetchWebTool(FunctionTool):
    """使用 curl + trafilatura 抓取并提取网页主要内容。"""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        max_output_chars: int = 20000,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ) -> None:
        self._timeout = timeout
        self._max_output_chars = max_output_chars
        self._user_agent = user_agent

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="fetchWeb",
            description=(
                "获取网页的主要内容。输入一个网页 URL，使用本地 curl 抓取 HTML，"
                "并用 trafilatura 提取正文转换为 Markdown，返回 Markdown 正文及原始 URL。"
                "适合阅读文章、文档等页面以减少导航、广告等无关内容。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要获取的网页 URL",
                    }
                },
                "required": ["url"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        url = arguments.get("url")
        if not isinstance(url, str) or not url.strip():
            return "抓取失败：缺少必填参数 url（网页地址）。"

        target = url.strip()
        if not (target.startswith("http://") or target.startswith("https://")):
            return "抓取失败：url 必须以 http:// 或 https:// 开头。"

        try:
            html = await asyncio.to_thread(self._fetch_html, target)
        except subprocess.TimeoutExpired:
            return f"抓取失败：请求超时（{self._timeout:g} 秒），请稍后重试。"
        except FileNotFoundError:
            return "抓取失败：未找到本地 curl 程序。"
        except OSError as exc:
            return f"抓取失败：调用 curl 时发生系统错误（{exc}）。"
        except Exception as exc:  # noqa: BLE001
            return f"抓取失败：抓取网页时发生异常（{type(exc).__name__}: {exc}）。"

        if not html or not html.strip():
            return "抓取失败：未获取到网页 HTML 内容。"

        try:
            markdown = await asyncio.to_thread(self._extract_markdown, html, target)
        except Exception as exc:  # noqa: BLE001
            return f"抓取失败：HTML 解析或正文提取失败（{type(exc).__name__}: {exc}）。"

        if not markdown or not markdown.strip():
            return "抓取失败：无法从网页中提取正文内容，可能页面结构不适合提取或主要内容为空。"

        content = markdown.strip()
        if len(content) > self._max_output_chars:
            content = content[: self._max_output_chars] + "\n\n……（内容过长已截断）"

        lines = [
            f"URL：{target}",
            "",
            "Markdown 正文：",
            content,
        ]
        return "\n".join(lines)

    def _fetch_html(self, url: str) -> str:
        cmd = [
            "curl",
            "-L",
            "--silent",
            "--show-error",
            "--connect-timeout",
            str(int(self._timeout)),
            "--max-time",
            str(int(self._timeout)),
            "-A",
            self._user_agent,
            "-H",
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "-H",
            "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
            url,
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self._timeout,
            check=False,
            shell=False,
        )
        if result.returncode != 0:
            stderr = (result.stderr or b"").decode("utf-8", errors="ignore").strip()
            if stderr:
                raise OSError(stderr)
            raise OSError(f"curl 返回非零状态码：{result.returncode}")
        data = result.stdout or b""
        try:
            return data.decode("utf-8")
        except UnicodeError:
            try:
                return data.decode("gbk", errors="ignore")
            except Exception:
                return data.decode("latin-1", errors="ignore")

    def _extract_markdown(self, html: str, url: str) -> str:
        # 优先使用 include_comments=False、include_tables=True 等参数尽量保留结构
        downloaded = html
        result = trafilatura.extract(
            downloaded,
            url=url,
            include_comments=False,
            include_tables=True,
            include_links=True,
            include_images=False,
            output_format="markdown",
            favor_precision=True,
        )
        if result and result.strip():
            return result

        # 备选：不传 url 用于某些站点
        result = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            include_links=True,
            include_images=False,
            output_format="markdown",
            favor_precision=True,
        )
        return result or ""


__all__ = ["FetchWebTool"]
