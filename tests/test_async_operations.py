import pytest

from client.disk_client import DiskClient
from tests.helpers import await_success, operation_href, unique_path

pytestmark = pytest.mark.regression


def _make_nonempty_folder(client: DiskClient, make_folder) -> str:
    folder = make_folder("src")
    file_path = f"{folder}/file.txt"
    assert client.upload(file_path, b"async op content").status_code == 201
    return folder


def test_nonempty_folder_copy_is_async(client: DiskClient, test_folder: str, make_folder):
    src = _make_nonempty_folder(client, make_folder)
    dst = unique_path(test_folder, "copy-dst")

    await_success(client, operation_href(client.copy(src, dst)))

    assert client.list_meta(dst).status_code == 200
    assert client.list_meta(src).status_code == 200


def test_nonempty_folder_move_is_async(client: DiskClient, test_folder: str, make_folder):
    src = _make_nonempty_folder(client, make_folder)
    dst = unique_path(test_folder, "move-dst")

    await_success(client, operation_href(client.move(src, dst)))

    assert client.list_meta(dst).status_code == 200
    assert client.list_meta(src).status_code == 404


def test_nonempty_folder_delete_is_async(client: DiskClient, make_folder):
    src = _make_nonempty_folder(client, make_folder)

    await_success(client, operation_href(client.delete(src)))

    assert client.list_meta(src).status_code == 404
