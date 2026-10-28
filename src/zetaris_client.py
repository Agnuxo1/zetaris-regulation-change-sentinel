"""Minimal Zetaris REST client (SQL Editor endpoint).

Configuration comes from environment variables, optionally loaded from a
dotenv-style file named by ZETARIS_ENV_FILE. Credentials are never logged.

  ZETARIS_REST_URL   e.g. http://127.0.0.1:8888/api/v1.0
  ZETARIS_API_KEY + ZETARIS_ORG_ID              (bearer key created in the GUI), or
  ZETARIS_LOGIN_URL + ZETARIS_USERNAME + ZETARIS_PASSWORD   (local install login)
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request
import uuid


def _load_env_file() -> None:
    path = os.environ.get("ZETARIS_ENV_FILE")
    if not path or not pathlib.Path(path).exists():
        return
    alias = {"ZETARIS_ADMIN_EMAIL": "ZETARIS_USERNAME", "ZETARIS_ADMIN_PASSWORD": "ZETARIS_PASSWORD"}
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            key = alias.get(key.strip(), key.strip())
            os.environ.setdefault(key, value.strip().strip('"'))


def _post(url: str, payload: dict | None, headers: dict, timeout: float) -> tuple[int, bytes]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


class ZetarisError(RuntimeError):
    pass


class Zetaris:
    def __init__(self, timeout: float = 120.0):
        _load_env_file()
        self.rest = os.environ.get("ZETARIS_REST_URL", "http://127.0.0.1:8888/api/v1.0").rstrip("/")
        self.timeout = timeout
        key, org = os.environ.get("ZETARIS_API_KEY"), os.environ.get("ZETARIS_ORG_ID")
        if not (key and org):
            key, org = self._login()
        self._headers = {"Authorization": "Bearer " + key, "X-Org-ID": str(org)}

    def _login(self) -> tuple[str, str]:
        url = os.environ.get("ZETARIS_LOGIN_URL", "http://127.0.0.1:3000/api/auth/login")
        user, password = os.environ.get("ZETARIS_USERNAME"), os.environ.get("ZETARIS_PASSWORD")
        if not (user and password):
            raise ZetarisError("No Zetaris credentials configured (see .env.example)")
        code, body = _post(url, {"username": user, "password": password}, {}, self.timeout)
        text = body.decode(errors="replace")
        token = re.search(r"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}", text)
        org = re.search(r'"orgId"\s*:\s*(\d+)', text)
        if code != 200 or not token or not org:
            raise ZetarisError(f"Zetaris login failed (HTTP {code})")
        return token.group(0), org.group(1)

    def sql(self, statement: str, limit: int = 10000) -> dict:
        """Run one Lightning SQL statement; returns headers, rows, server and wall time."""
        t0 = time.perf_counter()
        code, body = _post(f"{self.rest}/sql-editor/sqls/run",
                           {"queryId": str(uuid.uuid4()), "sql": statement, "source": "SqlEditor", "limit": limit},
                           {**self._headers, "X-Request-ID": str(uuid.uuid4())}, self.timeout)
        wall = time.perf_counter() - t0
        doc = json.loads(body) if body[:1] in (b"{", b"[") else {}
        if code != 200 or doc.get("error") or doc.get("errors"):
            raise ZetarisError(f"SQL failed (HTTP {code}): {str(doc.get('msg') or doc)[:300]}")
        headers = doc.get("headers") or []
        return {"headers": headers, "rows": [dict(zip(headers, r)) for r in doc.get("data") or []],
                "server_ms": doc.get("timeUsed"), "wall_s": wall}
