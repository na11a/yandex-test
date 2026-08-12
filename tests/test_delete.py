import pytest

from client.disk_client import DiskClient
from tests.helpers import wait_for_meta_status


@pytest.mark.smoke
@pytest.mark.regression
def test_delete_file_to_trash(client: DiskClient, make_file):
    path = make_file()

    response = client.delete(path)
    assert response.status_code == 204, (
        f"expected 204 deleting {path}, got HTTP {response.status_code} {response.text}"
    )

    wait_for_meta_status(client, path, 404)


@pytest.mark.smoke
@pytest.mark.regression
def test_delete_empty_folder(client: DiskClient, make_folder):
    path = make_folder("empty-folder")

    response = client.delete(path)
    assert response.status_code == 204, (
        f"expected 204 deleting {path}, got HTTP {response.status_code} {response.text}"
    )

    wait_for_meta_status(client, path, 404)


@pytest.mark.regression
def test_delete_file_permanently(client: DiskClient, make_file):
    path = make_file()

    response = client.delete(path, permanently=True)
    assert response.status_code == 204, (
        f"expected 204 permanently deleting {path}, "
        f"got HTTP {response.status_code} {response.text}"
    )

    wait_for_meta_status(client, path, 404)
