import pytest
from jsonschema import validate

from client.disk_client import DiskClient
from conftest import load_schema

pytestmark = pytest.mark.regression


def test_disk_info_matches_schema(client: DiskClient):
    response = client.disk_info()
    assert response.status_code == 200, response.text
    validate(instance=response.json(), schema=load_schema("disk_info"))


def test_resource_meta_matches_schema(client: DiskClient, test_folder: str):
    response = client.list_meta(test_folder)
    assert response.status_code == 200, response.text
    validate(instance=response.json(), schema=load_schema("resource"))


def test_upload_href_matches_link_schema(client: DiskClient, test_folder: str):
    path = f"{test_folder}/schema-upload-target.txt"
    response = client.get_upload_href(path)
    assert response.status_code == 200, response.text
    validate(instance=response.json(), schema=load_schema("link"))
