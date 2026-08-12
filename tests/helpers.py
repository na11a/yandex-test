"""Shared test helpers: waiters for eventual consistency, async-operation utilities, path/schema tools."""

import json
import os
import time
import uuid
from typing import Callable, Optional

from client.disk_client import DiskClient

TRASH_ROOT = "trash:/"


def unique_path(test_folder: str, name: str) -> str:
    """Build a unique child path under the current test's root folder."""
    return f"{test_folder}/{uuid.uuid4()}-{name}"


def load_schema(name: str) -> dict:
    """Read a JSON schema file from the repo-root schemas/ directory by name (with or without .json)."""
    if not name.endswith(".json"):
        name = f"{name}.json"
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(repo_root, "schemas", name), encoding="utf-8") as fh:
        return json.load(fh)


def await_async(client: DiskClient, response) -> None:
    """Poll an async 202 operation to success; pass-through synchronous responses."""
    if response.status_code == 202:
        href = response.json().get("href")
        assert href, f"202 response without an 'href': {response.text}"
        status = client.wait_for_operation(href)
        assert status == "success", f"async operation did not succeed: {status}"


def operation_href(response) -> str:
    """Require the response to be an async 202 and return its operation href."""
    assert response.status_code == 202, (
        f"expected async 202, got HTTP {response.status_code} {response.text}"
    )
    href = response.json().get("href")
    assert href, f"202 response did not carry an operation href: {response.text}"
    return href


def await_success(client: DiskClient, href: str, timeout: int = 60) -> None:
    status = client.wait_for_operation(href, timeout=timeout)
    assert status == "success", f"operation {href} ended in status {status}"


def get_meta(client: DiskClient, path: str) -> dict:
    response = client.list_meta(path)
    assert response.status_code == 200, (
        f"list_meta {path} failed: HTTP {response.status_code} {response.text}"
    )
    return response.json()


def _wait_until(check: Callable[[], tuple], timeout: float, interval: float = 1.0) -> tuple:
    """Poll check() -> (done, value); return (done, last value) once done or the deadline passes."""
    deadline = time.monotonic() + timeout
    while True:
        done, value = check()
        if done or time.monotonic() >= deadline:
            return done, value
        time.sleep(interval)


def wait_for_meta_status(
    client: DiskClient, path: str, expected: int, timeout: float = 300.0, interval: float = 1.0
) -> None:
    """Poll list_meta(path) until it returns expected, absorbing backend index lag."""

    def check():
        status = client.list_meta(path).status_code
        return status == expected, status

    done, status = _wait_until(check, timeout, interval)
    assert done, (
        f"{path} did not reach HTTP {expected} within {timeout}s (last: HTTP {status})"
    )


def wait_for_public_state(
    client: DiskClient, path: str, published: bool, timeout: float = 120.0
) -> dict:
    """The meta index lags behind publish/unpublish; returns the last observed meta."""

    def check():
        meta = get_meta(client, path)
        is_public = bool(meta.get("public_url")) and bool(meta.get("public_key"))
        return is_public == published, meta

    _, meta = _wait_until(check, timeout)
    return meta


def find_in_trash(client: DiskClient, origin_path: str) -> Optional[dict]:
    """Return the trash item whose origin_path matches, paging through the trash root."""
    offset, limit = 0, 100
    while True:
        response = client.trash_list(TRASH_ROOT, limit=limit, offset=offset)
        assert response.status_code == 200, (
            f"trash_list failed: HTTP {response.status_code} {response.text}"
        )
        items = response.json().get("_embedded", {}).get("items", [])
        for item in items:
            if item.get("origin_path") == origin_path:
                return item
        if len(items) < limit:
            return None
        offset += limit


def wait_in_trash(client: DiskClient, origin_path: str, timeout: float = 30.0) -> dict:
    """Wait for an item to appear in trash and return it (trash is eventually consistent)."""

    def check():
        item = find_in_trash(client, origin_path)
        return item is not None, item

    done, item = _wait_until(check, timeout)
    assert done, f"item with origin_path {origin_path} never appeared in trash"
    return item


def wait_absent_from_trash(client: DiskClient, origin_path: str, timeout: float = 30.0) -> None:
    def check():
        return find_in_trash(client, origin_path) is None, None

    done, _ = _wait_until(check, timeout)
    assert done, f"item with origin_path {origin_path} still present in trash"
