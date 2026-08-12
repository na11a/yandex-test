import time
from typing import Optional

import pytest

from client.disk_client import DiskClient
from conftest import unique_path

pytestmark = pytest.mark.regression

TRASH_ROOT = "trash:/"


def _await_async(client: DiskClient, response) -> None:
    """Poll an async 202 operation to success; pass-through synchronous responses."""
    if response.status_code == 202:
        href = response.json().get("href")
        assert href, f"202 response without an 'href': {response.text}"
        status = client.wait_for_operation(href)
        assert status == "success", f"async operation did not succeed: {status}"


def _meta(client: DiskClient, path: str) -> dict:
    response = client.list_meta(path)
    assert response.status_code == 200, (
        f"list_meta {path} failed: HTTP {response.status_code} {response.text}"
    )
    return response.json()


def _wait_for_meta_status(
    client: DiskClient, path: str, expected: int, timeout: float = 60.0
) -> None:
    """Poll list_meta(path) until it returns expected, absorbing backend index lag."""
    deadline = time.monotonic() + timeout
    while True:
        status = client.list_meta(path).status_code
        if status == expected:
            return
        if time.monotonic() >= deadline:
            raise AssertionError(
                f"{path} did not reach HTTP {expected} within {timeout}s "
                f"(last: HTTP {status})"
            )
        time.sleep(1.0)


def _wait_for_public_state(
    client: DiskClient, path: str, published: bool, timeout: float = 60.0
) -> dict:
    """The meta index lags behind publish/unpublish; returns the last observed meta."""
    deadline = time.monotonic() + timeout
    while True:
        meta = _meta(client, path)
        if bool(meta.get("public_url")) == published or time.monotonic() >= deadline:
            return meta
        time.sleep(1.0)


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


def _wait_in_trash(client: DiskClient, origin_path: str, timeout: float = 30.0) -> dict:
    """Wait for an item to appear in trash (trash listing is eventually consistent)."""
    deadline = time.monotonic() + timeout
    while True:
        item = _find_in_trash(client, origin_path)
        if item is not None:
            return item
        if time.monotonic() >= deadline:
            raise AssertionError(
                f"item with origin_path {origin_path} never appeared in trash"
            )
        time.sleep(1.0)


def test_full_resource_lifecycle(client: DiskClient, test_folder: str):
    # 1) Create a working subfolder.
    folder = unique_path(test_folder, "e2e")
    created = client.mkdir(folder)
    assert created.status_code == 201, (
        f"mkdir {folder}: HTTP {created.status_code} {created.text}"
    )
    assert _meta(client, folder)["type"] == "dir"

    # 2) Upload known bytes via the two-step flow (GET upload href, PUT bytes).
    original = f"{folder}/original.bin"
    content = b"e2e lifecycle payload \x00\x01\x02 \xff"
    href_response = client.get_upload_href(original)
    assert href_response.status_code == 200, (
        f"get_upload_href {original}: "
        f"HTTP {href_response.status_code} {href_response.text}"
    )
    assert href_response.json().get("href")
    uploaded = client.upload(original, content)
    assert uploaded.status_code == 201, (
        f"upload {original}: HTTP {uploaded.status_code} {uploaded.text}"
    )
    meta = _meta(client, original)
    assert meta["type"] == "file", f"uploaded resource is not a file: {meta}"
    assert meta["size"] == len(content), f"uploaded size mismatch: {meta}"

    # 3) Copy the file within the folder; both source and copy must exist.
    copy_path = f"{folder}/copy.bin"
    copied = client.copy(original, copy_path)
    assert copied.status_code == 201, (
        f"copy {original} -> {copy_path}: HTTP {copied.status_code} {copied.text}"
    )
    _wait_for_meta_status(client, copy_path, 200)
    assert client.list_meta(original).status_code == 200

    # 4) Publish the copy; its meta must expose a public_url.
    published = client.publish(copy_path)
    assert published.status_code == 200, (
        f"publish {copy_path}: HTTP {published.status_code} {published.text}"
    )
    meta = _wait_for_public_state(client, copy_path, published=True)
    assert meta.get("public_url"), f"public_url missing after publish: {meta}"

    # 5) Download the original (GET download href, GET bytes) and verify content.
    download_href = client.get_download_href(original)
    assert download_href.status_code == 200, (
        f"get_download_href {original}: "
        f"HTTP {download_href.status_code} {download_href.text}"
    )
    assert download_href.json().get("href")
    assert client.download(original) == content

    # 6) Unpublish the copy; public_url must disappear.
    unpublished = client.unpublish(copy_path)
    assert unpublished.status_code == 200, (
        f"unpublish {copy_path}: HTTP {unpublished.status_code} {unpublished.text}"
    )
    meta = _wait_for_public_state(client, copy_path, published=False)
    assert meta.get("public_url") is None, (
        f"public_url still present after unpublish: {meta}"
    )

    # 7) Delete the copy to trash; its path must become 404.
    deleted = client.delete(copy_path)
    assert deleted.status_code in (202, 204), (
        f"delete-to-trash {copy_path}: HTTP {deleted.status_code} {deleted.text}"
    )
    _await_async(client, deleted)
    _wait_for_meta_status(client, copy_path, 404)

    # 8) Restore the copy from trash back to its origin.
    trash_item = _wait_in_trash(client, copy_path)
    restored = client.trash_restore(trash_item["path"], overwrite=True)
    assert restored.status_code in (201, 202), (
        f"trash_restore {trash_item['path']}: "
        f"HTTP {restored.status_code} {restored.text}"
    )
    _await_async(client, restored)
    _wait_for_meta_status(client, copy_path, 200)
    assert _meta(client, copy_path).get("path") == copy_path

    # 9) Permanently delete the copy; it must be gone for good.
    purged = client.delete(copy_path, permanently=True)
    assert purged.status_code in (202, 204), (
        f"permanent delete {copy_path}: HTTP {purged.status_code} {purged.text}"
    )
    _await_async(client, purged)
    _wait_for_meta_status(client, copy_path, 404)
