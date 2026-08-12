import time
from typing import Optional

import pytest

from client.disk_client import DiskClient

pytestmark = pytest.mark.regression

TRASH_ROOT = "trash:/"


def _await_async(client: DiskClient, response) -> None:
    """Poll an async 202 operation to success; pass-through synchronous responses."""
    if response.status_code == 202:
        href = response.json().get("href")
        assert href, f"202 response without an 'href': {response.text}"
        status = client.wait_for_operation(href)
        assert status == "success", f"async operation did not succeed: {status}"


def _find_in_trash(client: DiskClient, origin_path: str) -> Optional[dict]:
    """Return the trash item whose origin_path matches, paging through the trash root."""
    offset, limit = 0, 100
    while True:
        response = client.trash_list(TRASH_ROOT, limit=limit, offset=offset)
        assert response.status_code == 200, (
            f"trash_list failed: HTTP {response.status_code} {response.text}"
        )
        items = response.json().get("_embedded", {}).get("items", [])
        for item in items:
            if item.get("origin_path") == origin_path:
                return item
        if len(items) < limit:
            return None
        offset += limit


def _wait_in_trash(client: DiskClient, origin_path: str, timeout: int = 30) -> dict:
    """Wait for an item to appear in trash and return it (trash is eventually consistent)."""
    deadline = time.monotonic() + timeout
    while True:
        item = _find_in_trash(client, origin_path)
        if item is not None:
            return item
        if time.monotonic() >= deadline:
            raise AssertionError(f"item with origin_path {origin_path} never appeared in trash")
        time.sleep(1.0)


def _wait_absent_from_trash(client: DiskClient, origin_path: str, timeout: int = 30) -> None:
    deadline = time.monotonic() + timeout
    while True:
        if _find_in_trash(client, origin_path) is None:
            return
        if time.monotonic() >= deadline:
            raise AssertionError(f"item with origin_path {origin_path} still present in trash")
        time.sleep(1.0)


def test_delete_to_trash_lists_the_item(client: DiskClient, make_file):
    file_path = make_file(name="to-trash.txt")

    deleted = client.delete(file_path, permanently=False)
    assert deleted.status_code in (202, 204), (
        f"delete-to-trash returned unexpected status: "
        f"HTTP {deleted.status_code} {deleted.text}"
    )
    _await_async(client, deleted)

    assert client.list_meta(file_path).status_code == 404

    item = _wait_in_trash(client, file_path)
    try:
        assert item["origin_path"] == file_path
        assert item.get("path", "").startswith("trash:/")
    finally:
        _await_async(client, client.trash_delete(item["path"]))


def test_restore_from_trash_returns_file_to_origin(client: DiskClient, make_file):
    file_path = make_file(name="to-restore.txt")

    deleted = client.delete(file_path, permanently=False)
    assert deleted.status_code in (202, 204), (
        f"delete-to-trash returned unexpected status: "
        f"HTTP {deleted.status_code} {deleted.text}"
    )
    _await_async(client, deleted)

    item = _wait_in_trash(client, file_path)
    trash_path = item["path"]

    restored = client.trash_restore(trash_path, overwrite=True)
    assert restored.status_code in (201, 202), (
        f"trash_restore returned unexpected status: "
        f"HTTP {restored.status_code} {restored.text}"
    )
    _await_async(client, restored)

    meta = client.list_meta(file_path)
    assert meta.status_code == 200, (
        f"restored file not found at origin: HTTP {meta.status_code} {meta.text}"
    )
    assert meta.json().get("path") == file_path

    _wait_absent_from_trash(client, file_path)


def test_delete_from_trash_removes_the_item(client: DiskClient, make_file):
    file_path = make_file(name="to-purge.txt")

    deleted = client.delete(file_path, permanently=False)
    assert deleted.status_code in (202, 204), (
        f"delete-to-trash returned unexpected status: "
        f"HTTP {deleted.status_code} {deleted.text}"
    )
    _await_async(client, deleted)

    item = _wait_in_trash(client, file_path)
    trash_path = item["path"]

    purged = client.trash_delete(trash_path)
    assert purged.status_code in (202, 204), (
        f"trash_delete returned unexpected status: "
        f"HTTP {purged.status_code} {purged.text}"
    )
    _await_async(client, purged)

    _wait_absent_from_trash(client, file_path)
