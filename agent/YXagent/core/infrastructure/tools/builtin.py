"""内置工具集的装配入口。"""

from __future__ import annotations

from core.config import AppConfig
from core.infrastructure.tools.datetime_tools import GetDateTool, IsLeapYearTool
from core.infrastructure.tools.file_tools import (
    CreateDirectoryTool,
    CreateFileTool,
    DeleteFileTool,
    EditFileTool,
    GetFileTypeTool,
    GetWorkingDirectoryTool,
    ListDirectoryTool,
    ReadFileTool,
    RemoveDirectoryTool,
    RenamePathTool,
)
from core.infrastructure.tools.filesystem_service import FileSystemService
from core.infrastructure.tools.cli_run import RunCliTool
from core.infrastructure.tools.web_fetch import FetchWebTool
from core.infrastructure.tools.web_search import SearchWebTool
from core.ports.tools import ToolRegistry


def build_default_registry(config: AppConfig) -> ToolRegistry:
    """根据配置装配默认工具注册表。

    新增工具时只需在这里注册一次，所有前端立即可用。
    """
    service = FileSystemService(config.workspace, max_read_chars=config.agent.max_read_chars)

    registry = ToolRegistry()
    registry.register(GetDateTool())
    registry.register(IsLeapYearTool())
    registry.register(GetWorkingDirectoryTool(service))
    registry.register(ListDirectoryTool(service))
    registry.register(GetFileTypeTool(service))
    registry.register(ReadFileTool(service))
    registry.register(CreateFileTool(service))
    registry.register(EditFileTool(service))
    registry.register(CreateDirectoryTool(service))
    registry.register(RemoveDirectoryTool(service))
    registry.register(DeleteFileTool(service))
    registry.register(RenamePathTool(service))
    registry.register(
        SearchWebTool(
            config.search.baidu_qianfan_api_key,
            model=config.search.model,
            timeout=config.search.timeout,
        )
    )
    registry.register(FetchWebTool(timeout=config.search.timeout))
    registry.register(RunCliTool(timeout=60.0))
    return registry


__all__ = ["build_default_registry"]
