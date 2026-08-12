import pytest

from client.disk_client import DiskClient
from tests.helpers import unique_path


@pytest.mark.smoke
@pytest.mark.regression
def test_mkdir_creates_subfolder(client: DiskClient, test_folder: str):
    path = unique_path(test_folder, "subdir")

    response = client.mkdir(path)
    assert response.status_code == 201, (
        f"mkdir {path}: HTTP {response.status_code} {response.text}"
    )

    meta = client.list_meta(path)
    assert meta.status_code == 200, (
        f"list_meta {path}: HTTP {meta.status_code} {meta.text}"
    )
    assert meta.json()["type"] == "dir"


@pytest.mark.smoke
@pytest.mark.regression
def test_two_step_upload(client: DiskClient, test_folder: str):
    path = unique_path(test_folder, "upload.bin")
    content = b"two-step upload payload"

    href_response = client.get_upload_href(path)
    assert href_response.status_code == 200, (
        f"get_upload_href {path}: HTTP {href_response.status_code} {href_response.text}"
    )
    assert href_response.json().get("href")

    upload = client.upload(path, content)
    assert upload.status_code == 201, (
        f"upload {path}: HTTP {upload.status_code} {upload.text}"
    )

    meta = client.list_meta(path)
    assert meta.status_code == 200, (
        f"list_meta {path}: HTTP {meta.status_code} {meta.text}"
    )
    body = meta.json()
    assert body["type"] == "file"
    assert body["size"] == len(content)
    assert body.get("md5")


@pytest.mark.smoke
@pytest.mark.regression
def test_download_round_trip(client: DiskClient, test_folder: str):
    path = unique_path(test_folder, "roundtrip.bin")
    content = b"round-trip content \x00\x01\x02 \xff bytes"

    upload = client.upload(path, content)
    assert upload.status_code == 201, (
        f"upload {path}: HTTP {upload.status_code} {upload.text}"
    )

    assert client.download(path) == content


@pytest.mark.regression
def test_upload_overwrite(client: DiskClient, test_folder: str):
    path = unique_path(test_folder, "overwrite.bin")

    first = client.upload(path, b"original content")
    assert first.status_code == 201, (
        f"initial upload {path}: HTTP {first.status_code} {first.text}"
    )

    new_content = b"overwritten content"
    second = client.upload(path, new_content, overwrite=True)
    assert second.status_code == 201, (
        f"overwrite upload {path}: HTTP {second.status_code} {second.text}"
    )

    assert client.download(path) == new_content
