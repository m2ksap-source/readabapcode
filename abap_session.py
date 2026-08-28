"""A tiny, headless session for the ABAP Development Tools (ADT) REST API
on an SAP BTP ABAP Environment (trial) system.

There is no browser and no SSO popup here. Authentication uses the OAuth 2.0
password grant against the XSUAA token endpoint: the script logs in as your
own BTP/ABAP developer user (ABAP_USERNAME / ABAP_PASSWORD), authenticating
the OAuth client with the CLIENT_ID / CLIENT_SECRET from a service key.

The access token is cached until shortly before it expires, so a script that
reads many objects only authenticates once.
"""

from __future__ import annotations

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT = 30


class AbapSession:
    def __init__(self) -> None:
        self.host = _require("ABAP_HOST").rstrip("/")
        self.oauth_url = _require("OAUTH_URL").rstrip("/")
        self.client_id = _require("CLIENT_ID")
        self.client_secret = _require("CLIENT_SECRET")
        self.sap_client = os.getenv("SAP_CLIENT", "100")
        self._user = _require("ABAP_USERNAME")
        self._password = _require("ABAP_PASSWORD")
        self._token = ""
        self._expires_at = 0.0

    # -- authentication ---------------------------------------------------
    def _access_token(self) -> str:
        if self._token and time.time() < self._expires_at:
            return self._token

        data = {
            "grant_type": "password",
            "username": self._user,
            "password": self._password,
        }

        resp = requests.post(
            f"{self.oauth_url}/oauth/token",
            data=data,
            auth=(self.client_id, self.client_secret),
            timeout=TIMEOUT,
        )
        if not resp.ok:
            raise SystemExit(
                f"OAuth token request failed ({resp.status_code}): {resp.text[:300]}"
            )
        body = resp.json()
        self._token = body["access_token"]
        # refresh a minute early to avoid using an almost-expired token
        self._expires_at = time.time() + body.get("expires_in", 3600) - 60
        return self._token

    # -- one GET against the ADT API -----------------------------------
    def get(self, path: str, accept: str = "text/plain") -> str:
        resp = requests.get(
            f"{self.host}{path}",
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "Accept": accept,
            },
            params={"sap-client": self.sap_client},
            timeout=TIMEOUT,
        )
        if resp.status_code == 404:
            raise LookupError(f"Object not found: {path}")
        if resp.status_code in (401, 403):
            raise PermissionError(
                f"{resp.status_code} for {path}. Your user needs ADT / developer "
                "read authorization for this object."
            )
        resp.raise_for_status()
        # ADT returns CRLF line endings; normalise to plain LF.
        return resp.text.replace("\r\n", "\n").replace("\r", "\n")


def _require(name: str) -> str:
    try:
        return os.environ[name]
    except KeyError:
        raise SystemExit(
            f"Missing environment variable {name!r}. "
            "Copy .env.example to .env and fill it in."
        )
