import pytest

from client.disk_client import DiskClient
from conftest import unique_path


def _assert_error_body(response):
    """Yandex.Disk error bodies are JSON carrying error/description/message."""
    body = response.json()
    assert body.get("error"), f"missing 'error' in body: {body}"
    assert body.get("description") or body.get("message"), (
        f"missing 'description'/'message' in body: {body}"
    )


@pytest.mark.smoke
@pytest.mark.regression
def test_bad_token_returns_401():
    bad_client = DiskClient(token="definitely-not-a-valid-token")
    response = bad_client.disk_info()
    try:
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )
        _assert_error_body(response)
    finally:
        bad_client.session.close()


@pytest.mark.regression
def test_missing_path_returns_404(client: DiskClient, test_folder: str):
    missing = unique_path(test_folder, "does-not-exist")
    response = client.list_meta(missing)
    assert response.status_code == 404, (
        f"expected 404, got {response.status_code}: {response.text}"
    )
    _assert_error_body(response)


@pytest.mark.regression
def test_mkdir_existing_folder_returns_409(client: DiskClient, test_folder: str):
    path = unique_path(test_folder, "conflict-dir")
    created = client.mkdir(path)
    assert created.status_code == 201, (
        f"setup mkdir failed: HTTP {created.status_code} {created.text}"
    )
    response = client.mkdir(path)
    assert response.status_code == 409, (
        f"expected 409, got {response.status_code}: {response.text}"
    )
    _assert_error_body(response)


@pytest.mark.regression
def test_upload_no_overwrite_over_existing_file_returns_409(
    client: DiskClient, make_file
):
    path = make_file(name="existing.txt", content=b"original")
    response = client.get_upload_href(path, overwrite=False)
    assert response.status_code == 409, (
        f"expected 409, got {response.status_code}: {response.text}"
    )
    _assert_error_body(response)
