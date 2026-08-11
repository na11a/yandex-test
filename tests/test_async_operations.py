import pytest

from client.disk_client import DiskClient
from conftest import unique_path

pytestmark = pytest.mark.regression

POLL_TIMEOUT = 60


def _make_nonempty_folder(client: DiskClient, test_folder: str) -> str:
    folder = unique_path(test_folder, "src")
    assert client.mkdir(folder).status_code == 201
    file_path = f"{folder}/file.txt"
    assert client.upload(file_path, b"async op content").status_code == 201
    return folder


def _operation_href(response) -> str:
    assert response.status_code == 202, (
        f"expected async 202, got HTTP {response.status_code} {response.text}"
    )
    href = response.json().get("href")
    assert href, f"202 response did not carry an operation href: {response.text}"
    return href


def _await_success(client: DiskClient, href: str) -> None:
    status = client.wait_for_operation(href, timeout=POLL_TIMEOUT)
    assert status == "success", f"operation {href} ended in status {status}"


def test_nonempty_folder_copy_is_async(client: DiskClient, test_folder: str):
    src = _make_nonempty_folder(client, test_folder)
    dst = unique_path(test_folder, "copy-dst")

    _await_success(client, _operation_href(client.copy(src, dst)))

    assert client.list_meta(dst).status_code == 200
    assert client.list_meta(src).status_code == 200


def test_nonempty_folder_move_is_async(client: DiskClient, test_folder: str):
    src = _make_nonempty_folder(client, test_folder)
    dst = unique_path(test_folder, "move-dst")

    _await_success(client, _operation_href(client.move(src, dst)))

    assert client.list_meta(dst).status_code == 200
    assert client.list_meta(src).status_code == 404


def test_nonempty_folder_delete_is_async(client: DiskClient, test_folder: str):
    src = _make_nonempty_folder(client, test_folder)

    _await_success(client, _operation_href(client.delete(src)))

    assert client.list_meta(src).status_code == 404
