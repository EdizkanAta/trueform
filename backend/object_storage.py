"""Object storage via Emergent Managed Object Storage.

The app never talks to storage directly — only this module does, and only the
backend holds EMERGENT_LLM_KEY. Objects are private; ownership lives in MongoDB.
"""
import os
from typing import Tuple

import requests
from starlette.concurrency import run_in_threadpool

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "trueform"

_storage_key = None


def _init_sync() -> str:
    global _storage_key
    if _storage_key:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def _put_sync(path: str, data: bytes, content_type: str) -> dict:
    global _storage_key
    key = _init_sync()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    if resp.status_code == 503:  # stale key -> reset + retry once
        _storage_key = None
        key = _init_sync()
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120,
        )
    resp.raise_for_status()
    return resp.json()


def _get_sync(path: str) -> Tuple[bytes, str]:
    key = _init_sync()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


async def init_storage() -> None:
    await run_in_threadpool(_init_sync)


async def put_object(path: str, data: bytes, content_type: str) -> dict:
    return await run_in_threadpool(_put_sync, path, data, content_type)


async def get_object(path: str) -> Tuple[bytes, str]:
    return await run_in_threadpool(_get_sync, path)


def object_path(user_id: str, ext: str, uid: str) -> str:
    return f"{APP_NAME}/uploads/{user_id}/{uid}.{ext}"
