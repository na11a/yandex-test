import pytest

from client.disk_client import DiskClient

pytestmark = pytest.mark.regression


@pytest.mark.parametrize(
    "filename",
    [
        pytest.param("plain.txt", id="plain"),
        pytest.param("name with spaces.txt", id="spaces"),
        pytest.param("файл-кириллица.txt", id="cyrillic"),
        pytest.param("emoji-🚀-file.txt", id="emoji"),
    ],
)
def test_upload_over_filenames(client: DiskClient, test_folder: str, filename: str):
    path = f"{test_folder}/{filename}"

    upload = client.upload(path, b"parametrized upload")
    assert upload.status_code == 201, (
        f"failed to upload {path}: HTTP {upload.status_code} {upload.text}"
    )

    meta = client.list_meta(path)
    assert meta.status_code == 200, (
        f"expected {path} to exist: HTTP {meta.status_code} {meta.text}"
    )
    assert meta.json()["name"] == filename


@pytest.mark.parametrize(
    "foldername",
    [
        pytest.param("subfolder", id="plain"),
        pytest.param("папка", id="cyrillic"),
        pytest.param("folder 🚀", id="emoji-spaces"),
    ],
)
def test_create_and_delete_over_foldernames(
    client: DiskClient, test_folder: str, foldername: str
):
    path = f"{test_folder}/{foldername}"

    created = client.mkdir(path)
    assert created.status_code == 201, (
        f"failed to create {path}: HTTP {created.status_code} {created.text}"
    )

    meta = client.list_meta(path)
    assert meta.status_code == 200
    assert meta.json()["name"] == foldername

    deleted = client.delete(path, permanently=True)
    assert deleted.status_code == 204, (
        f"failed to delete {path}: HTTP {deleted.status_code} {deleted.text}"
    )

    gone = client.list_meta(path)
    assert gone.status_code == 404
