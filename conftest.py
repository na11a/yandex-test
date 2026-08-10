import json
import os
import uuid

import pytest

from client.disk_client import DiskClient


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
        if cleanup.status_code == 202:
            # Non-empty folder delete is async; poll it to completion and
            # confirm success so the folder is actually gone before the next test.
            href = cleanup.json().get("href")
            if not href:
                raise AssertionError(
                    f"async delete for {path} returned 202 without an 'href': "
                    f"{cleanup.text}"
                )
            status = client.wait_for_operation(href)
            if status != "success":
                raise AssertionError(
                    f"delete operation for {path} did not succeed: {status}"
                )
        elif cleanup.status_code not in (204, 404):
            raise AssertionError(
                f"unexpected teardown status for {path}: "
                f"HTTP {cleanup.status_code} {cleanup.text}"
            )


def unique_path(test_folder: str, name: str) -> str:
    """Build a unique child path under the current test's root folder."""
    return f"{test_folder}/{uuid.uuid4()}-{name}"


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


def load_schema(name: str) -> dict:
    """Read a JSON schema file from the schemas/ directory by name (with or without .json)."""
    if not name.endswith(".json"):
        name = f"{name}.json"
    schema_path = os.path.join(os.path.dirname(__file__), "schemas", name)
    with open(schema_path, encoding="utf-8") as fh:
        return json.load(fh)
