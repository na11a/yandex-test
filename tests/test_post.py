import pytest

from client.disk_client import DiskClient
from tests.helpers import unique_path, wait_for_meta_status


@pytest.mark.smoke
@pytest.mark.regression
def test_copy_file(client: DiskClient, test_folder: str, make_file):
    source = make_file("copy-src.txt")
    destination = unique_path(test_folder, "copy-dst.txt")

    response = client.copy(source, destination)
    assert response.status_code == 201, (
        f"copy {source} -> {destination}: HTTP {response.status_code} {response.text}"
    )

    wait_for_meta_status(client, destination, 200)
    assert client.list_meta(source).status_code == 200


@pytest.mark.smoke
@pytest.mark.regression
def test_move_file(client: DiskClient, test_folder: str, make_file):
    source = make_file("move-src.txt")
    destination = unique_path(test_folder, "move-dst.txt")

    response = client.move(source, destination)
    assert response.status_code == 201, (
        f"move {source} -> {destination}: HTTP {response.status_code} {response.text}"
    )

    wait_for_meta_status(client, destination, 200)
    wait_for_meta_status(client, source, 404)


@pytest.mark.regression
def test_copy_empty_folder(client: DiskClient, test_folder: str, make_folder):
    source = make_folder("copy-src-dir")
    destination = unique_path(test_folder, "copy-dst-dir")

    response = client.copy(source, destination)
    assert response.status_code == 201, (
        f"copy {source} -> {destination}: HTTP {response.status_code} {response.text}"
    )

    wait_for_meta_status(client, destination, 200)
    assert client.list_meta(source).status_code == 200


@pytest.mark.regression
def test_move_empty_folder(client: DiskClient, test_folder: str, make_folder):
    source = make_folder("move-src-dir")
    destination = unique_path(test_folder, "move-dst-dir")

    response = client.move(source, destination)
    assert response.status_code == 201, (
        f"move {source} -> {destination}: HTTP {response.status_code} {response.text}"
    )

    wait_for_meta_status(client, destination, 200)
    wait_for_meta_status(client, source, 404)
