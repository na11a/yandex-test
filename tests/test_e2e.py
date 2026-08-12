import pytest

from client.disk_client import DiskClient
from tests.helpers import (
    await_async,
    get_meta,
    unique_path,
    wait_for_meta_status,
    wait_for_public_state,
    wait_in_trash,
)

pytestmark = pytest.mark.regression


def test_full_resource_lifecycle(client: DiskClient, test_folder: str):
    # 1) Create a working subfolder.
    folder = unique_path(test_folder, "e2e")
    created = client.mkdir(folder)
    assert created.status_code == 201, (
        f"mkdir {folder}: HTTP {created.status_code} {created.text}"
    )
    assert get_meta(client, folder)["type"] == "dir"

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
    meta = get_meta(client, original)
    assert meta["type"] == "file", f"uploaded resource is not a file: {meta}"
    assert meta["size"] == len(content), f"uploaded size mismatch: {meta}"

    # 3) Copy the file within the folder; both source and copy must exist.
    copy_path = f"{folder}/copy.bin"
    copied = client.copy(original, copy_path)
    assert copied.status_code == 201, (
        f"copy {original} -> {copy_path}: HTTP {copied.status_code} {copied.text}"
    )
    wait_for_meta_status(client, copy_path, 200)
    assert client.list_meta(original).status_code == 200

    # 4) Publish the copy; its meta must expose a public_url.
    published = client.publish(copy_path)
    assert published.status_code == 200, (
        f"publish {copy_path}: HTTP {published.status_code} {published.text}"
    )
    meta = wait_for_public_state(client, copy_path, published=True)
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
    meta = wait_for_public_state(client, copy_path, published=False)
    assert meta.get("public_url") is None, (
        f"public_url still present after unpublish: {meta}"
    )

    # 7) Delete the copy to trash; its path must become 404.
    deleted = client.delete(copy_path)
    assert deleted.status_code in (202, 204), (
        f"delete-to-trash {copy_path}: HTTP {deleted.status_code} {deleted.text}"
    )
    await_async(client, deleted)
    wait_for_meta_status(client, copy_path, 404)

    # 8) Restore the copy from trash back to its origin.
    trash_item = wait_in_trash(client, copy_path)
    restored = client.trash_restore(trash_item["path"], overwrite=True)
    assert restored.status_code in (201, 202), (
        f"trash_restore {trash_item['path']}: "
        f"HTTP {restored.status_code} {restored.text}"
    )
    await_async(client, restored)
    wait_for_meta_status(client, copy_path, 200)
    assert get_meta(client, copy_path).get("path") == copy_path

    # 9) Permanently delete the copy; it must be gone for good.
    purged = client.delete(copy_path, permanently=True)
    assert purged.status_code in (202, 204), (
        f"permanent delete {copy_path}: HTTP {purged.status_code} {purged.text}"
    )
    await_async(client, purged)
    wait_for_meta_status(client, copy_path, 404)
