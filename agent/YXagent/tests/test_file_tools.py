"""文件系统工具测试。"""

from __future__ import annotations

import pytest

from core.infrastructure.tools.filesystem_service import FileSystemService


@pytest.fixture
def service(tmp_path):
    return FileSystemService(tmp_path, max_read_chars=100)


def test_create_and_read_file(service, tmp_path):
    result = service.create_file(str(tmp_path), "a.txt", "hello")
    assert "已创建文件" in result
    assert service.read_file(str(tmp_path / "a.txt")) == "hello"


def test_create_file_rejects_existing(service, tmp_path):
    service.create_file(str(tmp_path), "a.txt", "x")
    result = service.create_file(str(tmp_path), "a.txt", "y")
    assert "已存在" in result


def test_create_file_rejects_path_separator(service, tmp_path):
    result = service.create_file(str(tmp_path), "sub/a.txt", "x")
    assert "不能包含路径分隔符" in result


def test_edit_file_overwrites_content(service, tmp_path):
    service.create_file(str(tmp_path), "a.txt", "old")
    result = service.edit_file(str(tmp_path / "a.txt"), "new")
    assert "已编辑文件" in result
    assert service.read_file(str(tmp_path / "a.txt")) == "new"


def test_read_file_truncates_long_content(service, tmp_path):
    service.create_file(str(tmp_path), "big.txt", "x" * 500)
    text = service.read_file(str(tmp_path / "big.txt"))
    assert "已截断" in text
    assert len(text) < 500


def test_read_missing_file_returns_error(service, tmp_path):
    assert "文件不存在" in service.read_file(str(tmp_path / "nope.txt"))


def test_binary_file_is_rejected(service, tmp_path):
    (tmp_path / "bin.dat").write_bytes(b"\x00\x01\x02")
    assert "二进制文件" in service.read_file(str(tmp_path / "bin.dat"))


def test_list_directory_shows_entries(service, tmp_path):
    service.create_file(str(tmp_path), "a.txt", "x")
    service.create_directory(str(tmp_path / "sub"))
    listing = service.list_directory(str(tmp_path))
    assert "[FILE] a.txt" in listing
    assert "[DIR]  sub/" in listing


def test_directory_lifecycle(service, tmp_path):
    service.create_directory(str(tmp_path / "sub"))
    assert "路径已存在" in service.create_directory(str(tmp_path / "sub"))
    assert "已删除目录" in service.remove_directory(str(tmp_path / "sub"))


def test_delete_and_rename(service, tmp_path):
    service.create_file(str(tmp_path), "a.txt", "x")
    assert "已重命名文件" in service.rename_path(str(tmp_path / "a.txt"), "b.txt")
    assert "已删除文件" in service.delete_file(str(tmp_path / "b.txt"))


def test_rename_rejects_path_separator(service, tmp_path):
    service.create_file(str(tmp_path), "a.txt", "x")
    assert "不能包含路径分隔符" in service.rename_path(str(tmp_path / "a.txt"), "sub/b.txt")


def test_path_outside_workspace_is_rejected(service, tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(ValueError):
        service.read_file(str(outside))


def test_drive_root_is_rejected(service):
    with pytest.raises(ValueError):
        service.resolve("C:\\")
