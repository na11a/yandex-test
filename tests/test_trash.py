import pytest

from client.disk_client import DiskClient
from tests.helpers import TRASH_ROOT, await_async, wait_absent_from_trash, wait_in_trash

pytestmark = pytest.mark.regression


def test_delete_to_trash_lists_the_item(client: DiskClient, make_file):
    file_path = make_file(name="to-trash.txt")

    deleted = client.delete(file_path, permanently=False)
    assert deleted.status_code in (202, 204), (
        f"delete-to-trash returned unexpected status: "
        f"HTTP {deleted.status_code} {deleted.text}"
    )
    await_async(client, deleted)

    assert client.list_meta(file_path).status_code == 404

    item = wait_in_trash(client, file_path)
    try:
        assert item["origin_path"] == file_path
        assert item.get("path", "").startswith(TRASH_ROOT)
    finally:
        await_async(client, client.trash_delete(item["path"]))


def test_restore_from_trash_returns_file_to_origin(client: DiskClient, make_file):
    file_path = make_file(name="to-restore.txt")

    deleted = client.delete(file_path, permanently=False)
    assert deleted.status_code in (202, 204), (
        f"delete-to-trash returned unexpected status: "
        f"HTTP {deleted.status_code} {deleted.text}"
    )
    await_async(client, deleted)

    item = wait_in_trash(client, file_path)
    trash_path = item["path"]

    restored = client.trash_restore(trash_path, overwrite=True)
    assert restored.status_code in (201, 202), (
        f"trash_restore returned unexpected status: "
        f"HTTP {restored.status_code} {restored.text}"
    )
    await_async(client, restored)

    meta = client.list_meta(file_path)
    assert meta.status_code == 200, (
        f"restored file not found at origin: HTTP {meta.status_code} {meta.text}"
    )
    assert meta.json().get("path") == file_path

    wait_absent_from_trash(client, file_path)


def test_delete_from_trash_removes_the_item(client: DiskClient, make_file):
    file_path = make_file(name="to-purge.txt")

    deleted = client.delete(file_path, permanently=False)
    assert deleted.status_code in (202, 204), (
        f"delete-to-trash returned unexpected status: "
        f"HTTP {deleted.status_code} {deleted.text}"
    )
    await_async(client, deleted)

    item = wait_in_trash(client, file_path)
    trash_path = item["path"]

    purged = client.trash_delete(trash_path)
    assert purged.status_code in (202, 204), (
        f"trash_delete returned unexpected status: "
        f"HTTP {purged.status_code} {purged.text}"
    )
    await_async(client, purged)

    wait_absent_from_trash(client, file_path)
