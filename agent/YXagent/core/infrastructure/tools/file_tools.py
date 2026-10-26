"""文件系统工具（暴露给大模型的薄封装）。"""

from __future__ import annotations

from typing import Any

from core.domain.models import ToolSpec
from core.infrastructure.tools.base import FunctionTool, path_parameter
from core.infrastructure.tools.filesystem_service import FileSystemService


class _FileToolBase(FunctionTool):
    """持有文件系统服务实例的基类。"""

    def __init__(self, service: FileSystemService) -> None:
        self._service = service


class GetWorkingDirectoryTool(FunctionTool):
    """获取当前工作目录。"""

    def __init__(self, service: FileSystemService) -> None:
        self._service = service

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="getWorkingDirectory",
            description="获取当前工作目录的路径",
            parameters={"type": "object", "properties": {}, "required": []},
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        return str(self._service.workspace)


class ListDirectoryTool(_FileToolBase):
    """列出目录内容。"""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="listDirectory",
            description="列出指定目录下的所有文件和子目录",
            parameters={
                "type": "object",
                "properties": {"path": path_parameter("要列出的目录路径")},
                "required": ["path"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        return self._service.list_directory(arguments.get("path", ""))


class GetFileTypeTool(_FileToolBase):
    """获取文件类型。"""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="getFileType",
            description="获取指定文件的文件类型（扩展名、MIME类型、文本或二进制）",
            parameters={
                "type": "object",
                "properties": {"path": path_parameter("要检测的文件路径")},
                "required": ["path"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        return self._service.get_file_type(arguments.get("path", ""))


class ReadFileTool(_FileToolBase):
    """读取文件内容。"""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="readFile",
            description="获取指定文件的内容，仅支持纯文本格式文件",
            parameters={
                "type": "object",
                "properties": {"path": path_parameter("要读取的文件路径")},
                "required": ["path"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        return self._service.read_file(arguments.get("path", ""))


class CreateFileTool(_FileToolBase):
    """创建文件。"""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="createFile",
            description="根据指定的目录和文件名创建新文件，可选写入初始内容",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "新文件所在的目录路径"},
                    "filename": {"type": "string", "description": "新文件的文件名"},
                    "content": {"type": "string", "description": "文件的初始内容，可选，默认为空"},
                },
                "required": ["directory", "filename"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        return self._service.create_file(
            arguments.get("directory", ""),
            arguments.get("filename", ""),
            arguments.get("content", ""),
        )


class EditFileTool(_FileToolBase):
    """编辑文件。"""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="editFile",
            description="编辑指定文件的内容（仅支持纯文本格式文件），用新内容覆盖原文件",
            parameters={
                "type": "object",
                "properties": {
                    "path": path_parameter("要编辑的文件路径"),
                    "content": {"type": "string", "description": "文件的新内容"},
                },
                "required": ["path", "content"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        return self._service.edit_file(arguments.get("path", ""), arguments.get("content", ""))


class CreateDirectoryTool(_FileToolBase):
    """创建目录。"""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="createDirectory",
            description="创建新目录",
            parameters={
                "type": "object",
                "properties": {"path": path_parameter("要创建的目录路径")},
                "required": ["path"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        return self._service.create_directory(arguments.get("path", ""))


class RemoveDirectoryTool(_FileToolBase):
    """删除目录。"""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="removeDirectory",
            description="删除指定目录及其全部内容（非空目录也可以删除）",
            parameters={
                "type": "object",
                "properties": {"path": path_parameter("要删除的目录路径")},
                "required": ["path"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        return self._service.remove_directory(arguments.get("path", ""))


class DeleteFileTool(_FileToolBase):
    """删除文件。"""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="deleteFile",
            description="删除指定文件",
            parameters={
                "type": "object",
                "properties": {"path": path_parameter("要删除的文件路径")},
                "required": ["path"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        return self._service.delete_file(arguments.get("path", ""))


class RenamePathTool(_FileToolBase):
    """重命名文件或目录。"""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="renamePath",
            description="重命名指定的文件或目录，新名称只能是文件名或目录名，不能包含路径",
            parameters={
                "type": "object",
                "properties": {
                    "path": path_parameter("要重命名的文件或目录路径"),
                    "new_name": {"type": "string", "description": "新的文件名或目录名（不含路径）"},
                },
                "required": ["path", "new_name"],
            },
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        return self._service.rename_path(arguments.get("path", ""), arguments.get("new_name", ""))


__all__ = [
    "CreateDirectoryTool",
    "CreateFileTool",
    "DeleteFileTool",
    "EditFileTool",
    "GetFileTypeTool",
    "GetWorkingDirectoryTool",
    "ListDirectoryTool",
    "ReadFileTool",
    "RemoveDirectoryTool",
    "RenamePathTool",
]
