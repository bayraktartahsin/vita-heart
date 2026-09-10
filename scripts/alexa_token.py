#!/usr/bin/env python3
"""Mint the Alexa surface's OAuth token and write it to a file, never to the terminal.

The page said "not connected" through a whole take: its first message would have opened
a consent page, on camera, mid-sentence. The household is connected once during setup,
the way a real one is connected once and then used daily, and the token is handed to the
page in the URL fragment — which the page strips from the address bar immediately.

    python scripts/alexa_token.py --out /tmp/vitaheart-alexa.token
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import secrets
import sys
from pathlib import Path

import httpx

API = os.environ.get("VITAHEART_API", "https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com")
CLIENT, HOUSEHOLD = "vita-heart-alexa", "AHMET1"


def mint() -> str | None:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    redirect = API + "/alexa-sim"
    with httpx.Client(follow_redirects=False, timeout=30) as cl:
        r = cl.post(f"{API}/oauth/approve",
                    params={"client_id": CLIENT, "redirect_uri": redirect,
                            "code_challenge": challenge, "state": "setup"},
                    data={"household": HOUSEHOLD})
        code = httpx.URL(r.headers.get("location", "")).params.get("code")
        if not code:
            return None
        return cl.post(f"{API}/oauth/token",
                       data={"grant_type": "authorization_code", "code": code,
                             "code_verifier": verifier, "client_id": CLIENT,
                             "redirect_uri": redirect}).json().get("access_token")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="file to write the token into (mode 600)")
    a = ap.parse_args()
    token = mint()
    if not token:
        print("could not mint an Alexa token; the page will ask for consent itself")
        return 1
    out = Path(a.out)
    out.write_text(token)
    out.chmod(0o600)
    print(f"alexa surface: connected (token written to {out}, not shown)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
