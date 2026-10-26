"""文件系统操作服务。

把"实际的文件操作"与"暴露给大模型的工具声明"分离：

* :class:`FileSystemService` —— 纯业务操作，可被其它应用层直接复用；
* ``file_tools.py`` —— 把上述操作包装成模型可调用的工具。

所有操作都在 ``workspace`` 目录范围内进行，越界路径会被拒绝，
避免模型误操作系统关键目录。
"""

from __future__ import annotations

import mimetypes
import os
import shutil
from pathlib import Path


class FileSystemService:
    """受工作目录约束的文件系统操作集合。"""

    def __init__(self, workspace: str | os.PathLike[str], max_read_chars: int = 8000) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.max_read_chars = max_read_chars

    # ------------------------------------------------------------------
    # 路径处理
    # ------------------------------------------------------------------
    def resolve(self, path: str) -> Path:
        """把用户/模型给出的路径解析为工作目录内的绝对路径。

        Raises:
            ValueError: 路径为空或逃逸出工作目录。
        """
        if not path or not path.strip():
            raise ValueError("路径不能为空")

        candidate = Path(path.strip()).expanduser()
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        resolved = Path(os.path.abspath(candidate))

        if _is_drive_root(resolved):
            raise ValueError(f"拒绝操作驱动器根目录: {resolved}")
        if not _is_within(resolved, self.workspace):
            raise ValueError(f"拒绝操作工作目录之外的路径: {resolved}")
        return resolved

    # ------------------------------------------------------------------
    # 读操作
    # ------------------------------------------------------------------
    def list_directory(self, path: str) -> str:
        """列出指定目录下的所有文件和子目录。"""
        target = self.resolve(path)
        if not target.is_dir():
            return f"错误: 目录不存在: {target}"

        lines: list[str] = []
        try:
            with os.scandir(target) as entries:
                for entry in sorted(entries, key=lambda e: (not e.is_dir(), e.name.lower())):
                    if entry.is_dir(follow_symlinks=False):
                        lines.append(f"[DIR]  {entry.name}/")
                    else:
                        try:
                            size = os.path.getsize(entry.path)
                        except OSError:
                            size = -1
                        lines.append(f"[FILE] {entry.name} ({size} bytes)")
        except PermissionError:
            return f"错误: 没有权限访问目录: {target}"

        if not lines:
            return f"目录为空: {target}"
        return "\n".join(lines)

    def get_file_type(self, path: str) -> str:
        """获取指定文件的文件类型。"""
        target = self.resolve(path)
        if not target.is_file():
            return f"错误: 文件不存在: {target}"

        ext = target.suffix or "(无扩展名)"
        mime, _ = mimetypes.guess_type(str(target))
        try:
            kind = _detect_kind(target)
        except OSError as exc:
            return f"错误: 无法读取文件: {exc}"
        size = target.stat().st_size
        return f"扩展名: {ext}, MIME类型: {mime or '未知'}, 内容类型: {kind}, 大小: {size} 字节"

    def read_file(self, path: str) -> str:
        """获取指定文件的内容（仅支持纯文本格式文件）。"""
        target = self.resolve(path)
        if not target.is_file():
            return f"错误: 文件不存在: {target}"

        try:
            data = target.read_bytes()
        except OSError as exc:
            return f"错误: 无法读取文件: {exc}"

        if b"\x00" in data:
            return f"错误: {target} 是二进制文件，仅支持读取纯文本格式文件"

        try:
            text = _decode_text(data)
        except ValueError as exc:
            return f"错误: {exc}"

        if len(text) > self.max_read_chars:
            text = text[: self.max_read_chars] + f"\n...(已截断，文件共 {len(text)} 字符)"
        return text

    # ------------------------------------------------------------------
    # 写操作
    # ------------------------------------------------------------------
    def create_file(self, directory: str, filename: str, content: str = "") -> str:
        """根据指定的目录和文件名创建新文件。"""
        if not filename or not filename.strip():
            return "错误: 文件名不能为空"
        if os.sep in filename.strip() or (os.altsep and os.altsep in filename.strip()):
            return "错误: 文件名不能包含路径分隔符"

        base = self.resolve(directory)
        full_path = base / filename.strip()

        if full_path.exists():
            return f"错误: 文件已存在: {full_path}"

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content or "", encoding="utf-8")
        except OSError as exc:
            return f"错误: 创建文件失败: {exc}"
        return f"已创建文件: {full_path}"

    def edit_file(self, path: str, content: str) -> str:
        """编辑指定文件的内容，用新内容覆盖原文件。"""
        target = self.resolve(path)
        if not target.is_file():
            return f"错误: 文件不存在: {target}"

        try:
            data = target.read_bytes()
        except OSError as exc:
            return f"错误: 无法读取文件: {exc}"

        if b"\x00" in data:
            return f"错误: {target} 是二进制文件，仅支持编辑纯文本格式文件"

        try:
            with open(target, "w", encoding="utf-8", newline="") as handle:
                handle.write(content if content is not None else "")
        except OSError as exc:
            return f"错误: 写入文件失败: {exc}"
        return f"已编辑文件: {target}，新内容 {len(content or '')} 个字符"

    def create_directory(self, path: str) -> str:
        """创建新目录。"""
        target = self.resolve(path)
        if target.exists():
            return f"错误: 路径已存在: {target}"
        try:
            target.mkdir(parents=True)
        except OSError as exc:
            return f"错误: 创建目录失败: {exc}"
        return f"已创建目录: {target}"

    def remove_directory(self, path: str) -> str:
        """删除目录及其全部内容。"""
        target = self.resolve(path)
        if not target.is_dir():
            return f"错误: 目录不存在: {target}"
        try:
            shutil.rmtree(target)
        except OSError as exc:
            return f"错误: 删除目录失败: {exc}"
        return f"已删除目录(含全部内容): {target}"

    def delete_file(self, path: str) -> str:
        """删除指定文件。"""
        target = self.resolve(path)
        if not target.is_file():
            return f"错误: 文件不存在: {target}"
        try:
            target.unlink()
        except OSError as exc:
            return f"错误: 删除文件失败: {exc}"
        return f"已删除文件: {target}"

    def rename_path(self, path: str, new_name: str) -> str:
        """重命名指定的文件或目录。"""
        if not new_name or not new_name.strip():
            return "错误: 新名称不能为空"
        if os.sep in new_name.strip() or (os.altsep and os.altsep in new_name.strip()):
            return "错误: 新名称不能包含路径分隔符，只能是文件名或目录名"

        target = self.resolve(path)
        if not target.exists():
            return f"错误: 文件或目录不存在: {target}"

        new_path = target.parent / new_name.strip()
        if new_path.exists():
            return f"错误: 新名称对应的路径已存在: {new_path}"

        try:
            target.rename(new_path)
        except OSError as exc:
            return f"错误: 重命名失败: {exc}"
        kind = "目录" if new_path.is_dir() else "文件"
        return f"已重命名{kind}: {target} -> {new_path}"


def _is_drive_root(path: Path) -> bool:
    """判断路径是否为驱动器根目录（如 ``C:\\``）。"""
    drive, _ = os.path.splitdrive(str(path))
    root = drive + os.sep
    return str(path).lower() == root.lower()


def _is_within(path: Path, root: Path) -> bool:
    """判断 path 是否位于 root 之内。"""
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _decode_text(data: bytes) -> str:
    """按常见编码解码文本内容。"""
    for encoding in ("utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别的文本编码")


def _detect_kind(path: Path) -> str:
    """判断文件是二进制还是文本。"""
    with open(path, "rb") as handle:
        head = handle.read(8192)
    if b"\x00" in head:
        return "二进制文件"
    try:
        head.decode("utf-8")
    except UnicodeDecodeError:
        return "文本文件(其他编码)"
    return "文本文件(UTF-8)"


__all__ = ["FileSystemService"]
