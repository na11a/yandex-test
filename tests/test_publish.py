import pytest

from client.disk_client import DiskClient
from tests.helpers import get_meta, wait_for_public_state

pytestmark = pytest.mark.regression


def test_publish_then_unpublish_toggles_public_url(client: DiskClient, make_file):
    path = make_file(name="publish-me.txt")

    assert get_meta(client, path).get("public_url") is None

    published = client.publish(path)
    assert published.status_code == 200, (
        f"publish {path} failed: HTTP {published.status_code} {published.text}"
    )

    meta = wait_for_public_state(client, path, published=True)
    public_key = meta.get("public_key")
    assert meta.get("public_url"), f"public_url missing after publish: {meta}"
    assert public_key, f"public_key missing after publish: {meta}"

    public = client.session.get(
        f"{client.base_url}/disk/public/resources",
        params={"public_key": public_key},
    )
    assert public.status_code == 200, (
        f"public metadata not reachable: HTTP {public.status_code} {public.text}"
    )

    unpublished = client.unpublish(path)
    assert unpublished.status_code == 200, (
        f"unpublish {path} failed: HTTP {unpublished.status_code} {unpublished.text}"
    )

    meta = wait_for_public_state(client, path, published=False)
    assert meta.get("public_url") is None, f"public_url still present after unpublish: {meta}"
    assert meta.get("public_key") is None, f"public_key still present after unpublish: {meta}"
