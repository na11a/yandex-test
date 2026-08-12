# Yandex.Disk REST API Autotests

Automated tests for the [Yandex.Disk REST API](https://yandex.ru/dev/disk/api/concepts/about-docpage/),
written in Python 3 with `pytest` and `requests`. The suite runs against the live production host
`https://cloud-api.yandex.net` (all paths under `/v1/`) and covers:

- **GET** — disk metadata, resource meta and folder listing, flat file list, last-uploaded,
  download/upload URL retrieval.
- **POST** — copy and move of files and folders.
- **PUT** — folder creation, the two-step file upload (get upload href, then PUT the bytes),
  and a download-and-verify round trip.
- **DELETE** — deleting files and folders, including `permanently=true`.
- Add-ons: negative/error cases (401/404/409), asynchronous operation polling (202 + operation
  status), publish/unpublish lifecycle, trash lifecycle (delete → restore → empty), parametrized
  data-driven cases, and JSON response schema validation (`jsonschema`).

There is no mock: tests hit production, so every test isolates itself inside a unique
`disk:/autotests-<uuid>` folder created by a fixture and removed in teardown regardless of outcome.

## Stack

- Python 3.10+
- `pytest` (test runner) + `requests` (HTTP client)
- `python-dotenv` — loads the token from a git-ignored `.env`
- `jsonschema` — response shape validation
- `pytest-html` — HTML report (JUnit XML comes from pytest core)

## Configuration

The token is read from the `YANDEX_DISK_TOKEN` environment variable, optionally loaded from a
git-ignored `.env` file at the repo root. Copy the example and fill in your token:

```bash
cp .env.example .env
# edit .env and set YANDEX_DISK_TOKEN
```

**Never commit the token.** `.env` is git-ignored; only `.env.example` (a placeholder) is
committed. Alternatively export it for the current shell:

```bash
export YANDEX_DISK_TOKEN=<your token>
```

## Running the tests

```bash
pytest                        # whole suite
pytest tests/test_get.py      # a single file
pytest -m smoke               # fast critical-path subset
pytest -m regression          # full functional coverage
```

**Do not run the tests in parallel** (e.g. `pytest -n <N>` via `pytest-xdist`): all tests share
one Disk account, and concurrent runs trigger transient server-side errors — HTTP 500
`InternalServerError` on publish/unpublish, stuck async operations, missing `public_url` after a
successful publish. Run the suite serially.

## Reports

Every run generates reports automatically (configured via `addopts` in `pytest.ini`):

- `report.html` — self-contained pytest-html report, open it in a browser;
- `report.xml` — JUnit XML for CI systems.

Both are git-ignored artifacts.

## API references

- API docs: https://yandex.ru/dev/disk/api/concepts/about-docpage/
- Interactive Polygon: https://yandex.ru/dev/disk/poligon/
