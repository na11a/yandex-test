import time

import pytest

from client.disk_client import DiskClient
from conftest import unique_path


def assert_gone(client: DiskClient, path: str, timeout: float = 120.0):
    """Poll list_meta until the resource is gone (404), tolerating delete propagation lag."""
    deadline = time.monotonic() + timeout
    while True:
        status = client.list_meta(path).status_code
        if status == 404:
            return
        if time.monotonic() >= deadline:
            raise AssertionError(f"{path} still present after delete: HTTP {status}")
        time.sleep(1.0)


@pytest.mark.smoke
@pytest.mark.regression
def test_delete_file_to_trash(client: DiskClient, make_file):
    path = make_file()

    response = client.delete(path)
    assert response.status_code == 204, (
        f"expected 204 deleting {path}, got HTTP {response.status_code} {response.text}"
    )

    assert_gone(client, path)


@pytest.mark.smoke
@pytest.mark.regression
def test_delete_empty_folder(client: DiskClient, test_folder: str):
    path = unique_path(test_folder, "empty-folder")
    assert client.mkdir(path).status_code == 201

    response = client.delete(path)
    assert response.status_code == 204, (
        f"expected 204 deleting {path}, got HTTP {response.status_code} {response.text}"
    )

    assert_gone(client, path)


@pytest.mark.regression
def test_delete_file_permanently(client: DiskClient, make_file):
    path = make_file()

    response = client.delete(path, permanently=True)
    assert response.status_code == 204, (
        f"expected 204 permanently deleting {path}, "
        f"got HTTP {response.status_code} {response.text}"
    )

    assert_gone(client, path)
