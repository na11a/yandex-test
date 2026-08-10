import time
from typing import Optional

import requests

import config


class OperationTimeout(RuntimeError):
    """Raised when an async Disk operation does not reach a terminal status in time."""


class DiskError(RuntimeError):
    """Raised when the API returns an error where a follow-up step expected data."""


def _bool(value: bool) -> str:
    """Serialize a bool as the lowercase 'true'/'false' the Disk API documents."""
    return "true" if value else "false"


class DiskClient:
    """Thin wrapper over the Yandex.Disk REST API exposing intent-level methods."""

    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        self.base_url = (base_url or config.BASE_URL).rstrip("/")
        token = token or config.get_token()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"OAuth {token}",
                "Accept": "application/json",
            }
        )

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    @staticmethod
    def _href(response: requests.Response, step: str) -> str:
        if not response.ok:
            raise DiskError(
                f"{step} failed: HTTP {response.status_code} {response.text}"
            )
        href = response.json().get("href")
        if not href:
            raise DiskError(f"{step} response did not contain an 'href': {response.text}")
        return href

    #
    # disk metadata
    #

    def disk_info(self) -> requests.Response:
        return self.session.get(self._url("/disk/"))

    #
    # resource meta / listing
    #

    def list_meta(self, path: str, **params) -> requests.Response:
        params["path"] = path
        return self.session.get(self._url("/disk/resources"), params=params)

    def list_files(self, **params) -> requests.Response:
        return self.session.get(self._url("/disk/resources/files"), params=params)

    def last_uploaded(self, **params) -> requests.Response:
        return self.session.get(self._url("/disk/resources/last-uploaded"), params=params)

    #
    # folder / resource mutation
    #

    def mkdir(self, path: str) -> requests.Response:
        return self.session.put(self._url("/disk/resources"), params={"path": path})

    def delete(self, path: str, permanently: bool = False, **params) -> requests.Response:
        params["path"] = path
        params["permanently"] = _bool(permanently)
        return self.session.delete(self._url("/disk/resources"), params=params)

    def copy(self, from_path: str, path: str, overwrite: bool = False) -> requests.Response:
        params = {"from": from_path, "path": path, "overwrite": _bool(overwrite)}
        return self.session.post(self._url("/disk/resources/copy"), params=params)

    def move(self, from_path: str, path: str, overwrite: bool = False) -> requests.Response:
        params = {"from": from_path, "path": path, "overwrite": _bool(overwrite)}
        return self.session.post(self._url("/disk/resources/move"), params=params)

    #
    # upload
    #

    def get_upload_href(self, path: str, overwrite: bool = False) -> requests.Response:
        params = {"path": path, "overwrite": _bool(overwrite)}
        return self.session.get(self._url("/disk/resources/upload"), params=params)

    def upload(self, path: str, content_bytes: bytes, overwrite: bool = False) -> requests.Response:
        href = self._href(self.get_upload_href(path, overwrite=overwrite), "get_upload_href")
        # Uploader host must not receive the OAuth header.
        return requests.put(href, data=content_bytes)

    #
    # download
    #

    def get_download_href(self, path: str) -> requests.Response:
        return self.session.get(self._url("/disk/resources/download"), params={"path": path})

    def download(self, path: str) -> bytes:
        href = self._href(self.get_download_href(path), "get_download_href")
        return requests.get(href).content

    #
    # publish
    #

    def publish(self, path: str) -> requests.Response:
        return self.session.put(self._url("/disk/resources/publish"), params={"path": path})

    def unpublish(self, path: str) -> requests.Response:
        return self.session.put(self._url("/disk/resources/unpublish"), params={"path": path})

    #
    # trash
    #

    def trash_list(self, path: Optional[str] = None, **params) -> requests.Response:
        if path is not None:
            params["path"] = path
        return self.session.get(self._url("/disk/trash/resources"), params=params)

    def trash_delete(self, path: Optional[str] = None) -> requests.Response:
        params = {}
        if path is not None:
            params["path"] = path
        return self.session.delete(self._url("/disk/trash/resources"), params=params)

    def trash_restore(
        self, path: str, name: Optional[str] = None, overwrite: bool = False
    ) -> requests.Response:
        params = {"path": path, "overwrite": _bool(overwrite)}
        if name is not None:
            params["name"] = name
        return self.session.put(self._url("/disk/trash/resources/restore"), params=params)

    #
    # async operations
    #

    def operation_status(self, op: str) -> requests.Response:
        if op.startswith("http"):
            url = op
        else:
            url = self._url(f"/disk/operations/{op}")
        return self.session.get(url)

    def wait_for_operation(self, href: str, timeout: int = 60, interval: float = 1.0) -> str:
        deadline = time.monotonic() + timeout
        while True:
            status = self.operation_status(href).json().get("status")
            if status in ("success", "failed"):
                return status
            if time.monotonic() >= deadline:
                raise OperationTimeout(
                    f"Operation {href} did not finish within {timeout}s (last status: {status})."
                )
            time.sleep(interval)
