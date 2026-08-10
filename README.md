# Yandex.Disk REST API Autotests

Automated tests for the [Yandex.Disk REST API](https://yandex.com/dev/disk-api/doc/en/index.md),
written in Python 3 with `pytest` and `requests`. The suite exercises the API's GET, POST, PUT and
DELETE methods against the live production host `https://cloud-api.yandex.net` (all paths under
`/v1/`), covering happy-path lifecycles, negative/error cases, asynchronous operation polling,
publish and trash lifecycles, parametrized cases, and JSON schema validation.

## Requirements

- Python 3.10+
- The dependencies pinned in `requirements.txt`: `pytest`, `requests`, `python-dotenv`,
  `jsonschema`, `pytest-html`.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Obtaining an OAuth token

The token authorises full read/write access to one account's Disk, so **use a non-personal
(throwaway/service) Yandex account**, never your personal one.

1. Register an "app for API access" at https://oauth.yandex.ru while logged into the throwaway
   account.
2. Grant the scopes `cloud_api:disk.read` and `cloud_api:disk.write` (add `cloud_api:disk.info`
   for quota assertions).
3. Obtain a token via the implicit flow, opening this URL in the browser session of the throwaway
   account and copying the token from the redirect fragment:
   `https://oauth.yandex.ru/authorize?response_type=token&client_id=<ClientID>`

## Configuration

The token is read from the `YANDEX_DISK_TOKEN` environment variable, optionally loaded from a
git-ignored `.env` file. Copy the example and fill in your token:

```bash
cp .env.example .env
# edit .env and set YANDEX_DISK_TOKEN
```

`.env` is git-ignored — never commit a real token. Only `.env.example` (a placeholder) is committed.

## Running the tests

```bash
pytest                 # run the whole suite
pytest -m smoke        # fast critical-path subset
pytest -m regression   # full functional coverage
```
