import time

import pytest

from client.disk_client import DiskClient
from conftest import unique_path


def _wait_for_status(client: DiskClient, path: str, expected: int, timeout: float = 5.0) -> int:
    """Poll list_meta(path) until it returns expected, absorbing the backend's
    brief post-move index lag; returns the last observed status code."""
    deadline = time.monotonic() + timeout
    status = client.list_meta(path).status_code
    while status != expected and time.monotonic() < deadline:
        time.sleep(0.5)
        status = client.list_meta(path).status_code
    return status


def _make_empty_folder(client: DiskClient, test_folder: str, name: str) -> str:
    path = unique_path(test_folder, name)
    assert client.mkdir(path).status_code == 201
    return path


@pytest.mark.smoke
def test_copy_file(client: DiskClient, test_folder: str, make_file):
    source = make_file("copy-src.txt")
    destination = unique_path(test_folder, "copy-dst.txt")

    response = client.copy(source, destination)
    assert response.status_code == 201, (
        f"copy {source} -> {destination}: HTTP {response.status_code} {response.text}"
    )

    assert _wait_for_status(client, destination, 200) == 200
    assert client.list_meta(source).status_code == 200


@pytest.mark.smoke
def test_move_file(client: DiskClient, test_folder: str, make_file):
    source = make_file("move-src.txt")
    destination = unique_path(test_folder, "move-dst.txt")

    response = client.move(source, destination)
    assert response.status_code == 201, (
        f"move {source} -> {destination}: HTTP {response.status_code} {response.text}"
    )

    assert _wait_for_status(client, destination, 200) == 200
    assert _wait_for_status(client, source, 404) == 404


@pytest.mark.regression
def test_copy_empty_folder(client: DiskClient, test_folder: str):
    source = _make_empty_folder(client, test_folder, "copy-src-dir")
    destination = unique_path(test_folder, "copy-dst-dir")

    response = client.copy(source, destination)
    assert response.status_code == 201, (
        f"copy {source} -> {destination}: HTTP {response.status_code} {response.text}"
    )

    assert _wait_for_status(client, destination, 200) == 200
    assert client.list_meta(source).status_code == 200


@pytest.mark.regression
def test_move_empty_folder(client: DiskClient, test_folder: str):
    source = _make_empty_folder(client, test_folder, "move-src-dir")
    destination = unique_path(test_folder, "move-dst-dir")

    response = client.move(source, destination)
    assert response.status_code == 201, (
        f"move {source} -> {destination}: HTTP {response.status_code} {response.text}"
    )

    assert _wait_for_status(client, destination, 200) == 200
    assert _wait_for_status(client, source, 404) == 404
