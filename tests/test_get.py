import uuid

import pytest

from client.disk_client import DiskClient


@pytest.mark.smoke
def test_disk_info(client: DiskClient):
    response = client.disk_info()
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body["total_space"], int)
    assert isinstance(body["used_space"], int)


@pytest.mark.smoke
def test_list_meta_on_test_folder(client: DiskClient, test_folder: str):
    response = client.list_meta(test_folder)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["type"] == "dir"
    assert body["path"] == test_folder


@pytest.mark.regression
def test_list_meta_embeds_uploaded_files(client: DiskClient, test_folder: str, make_file):
    first = make_file(name="a.txt")
    second = make_file(name="b.txt")

    response = client.list_meta(test_folder)
    assert response.status_code == 200, response.text
    body = response.json()

    listed = {item["path"] for item in body["_embedded"]["items"]}
    assert first in listed
    assert second in listed


@pytest.mark.regression
def test_list_files_finds_uploaded_file(client: DiskClient, test_folder: str, make_file):
    unique_name = f"find-me-{uuid.uuid4()}.txt"
    path = make_file(name=unique_name)

    response = client.list_files(limit=1000)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert isinstance(items, list)

    matches = [item for item in items if item["path"] == path]
    assert matches, f"uploaded file {path} not found in flat file list"
    assert matches[0]["type"] == "file"


@pytest.mark.regression
def test_last_uploaded_returns_items(client: DiskClient, test_folder: str, make_file):
    make_file(name="recent.txt")

    response = client.last_uploaded()
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert isinstance(items, list)


@pytest.mark.smoke
def test_get_upload_href(client: DiskClient, test_folder: str):
    path = f"{test_folder}/{uuid.uuid4()}-upload.txt"
    response = client.get_upload_href(path)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["href"]
    assert body["method"] == "PUT"


@pytest.mark.smoke
def test_get_download_href(client: DiskClient, test_folder: str, make_file):
    path = make_file(name="download.txt")

    response = client.get_download_href(path)
    assert response.status_code == 200, response.text
    assert response.json()["href"]
