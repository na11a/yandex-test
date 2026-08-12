import uuid

import pytest

from client.disk_client import DiskClient
from tests.helpers import await_async, unique_path


@pytest.fixture(scope="session")
def client() -> DiskClient:
    disk = DiskClient()
    yield disk
    disk.session.close()


@pytest.fixture
def test_folder(client: DiskClient):
    path = f"disk:/autotests-{uuid.uuid4()}"
    response = client.mkdir(path)
    assert response.status_code == 201, (
        f"failed to create test folder {path}: "
        f"HTTP {response.status_code} {response.text}"
    )
    try:
        yield path
    finally:
        cleanup = client.delete(path, permanently=True)
        assert cleanup.status_code in (202, 204, 404), (
            f"unexpected teardown status for {path}: "
            f"HTTP {cleanup.status_code} {cleanup.text}"
        )
        await_async(client, cleanup)


@pytest.fixture
def make_file(client: DiskClient, test_folder: str):
    """Factory that uploads small byte content to a unique child path and returns it."""

    def _make_file(name: str = "file.txt", content: bytes = b"autotest content") -> str:
        path = unique_path(test_folder, name)
        response = client.upload(path, content)
        assert response.status_code == 201, (
            f"failed to upload {path}: HTTP {response.status_code} {response.text}"
        )
        return path

    return _make_file


@pytest.fixture
def make_folder(client: DiskClient, test_folder: str):
    """Factory that creates a folder at a unique child path and returns it."""

    def _make_folder(name: str = "folder") -> str:
        path = unique_path(test_folder, name)
        response = client.mkdir(path)
        assert response.status_code == 201, (
            f"failed to create folder {path}: HTTP {response.status_code} {response.text}"
        )
        return path

    return _make_folder
