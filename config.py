import os

from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://cloud-api.yandex.net/v1"

TOKEN_ENV_VAR = "YANDEX_DISK_TOKEN"


def get_token() -> str:
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise RuntimeError(
            f"{TOKEN_ENV_VAR} is not set. Export it or add it to a git-ignored "
            f".env at the repo root (see .env.example)."
        )
    return token
