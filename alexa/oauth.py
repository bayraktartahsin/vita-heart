"""OAuth 2.1 with PKCE for one registered demo client.

Alexa+ requires: Streamable HTTP, OAuth 2.1 with PKCE (S256), and a plain 401
without WWW-Authenticate for anonymous calls. This is the smallest honest
implementation of that contract: one public client, S256 only, codes that live
five minutes, bearer tokens that live twelve hours, everything in DynamoDB so
the Lambda's statelessness does not matter. No secrets in the repo; the
"login" step is the household code, because the person authorising is the
household, not an Amazon account.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

REGION = os.environ.get("VITAHEART_REGION", "eu-north-1")
TABLE = os.environ.get("VITAHEART_TABLE", "vitaheart")
CLIENT_ID = "vita-heart-alexa"
CODE_TTL = 300
TOKEN_TTL = 12 * 3600

_table = None


def table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE)
    return _table


def reset_for_tests() -> None:
    global _table
    _table = None


def _s256(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def issue_code(client_id: str, redirect_uri: str, code_challenge: str, method: str, household: str, scope: str) -> str:
    if client_id != CLIENT_ID:
        raise ValueError("unknown client")
    if method != "S256" or not code_challenge:
        raise ValueError("PKCE S256 required")
    code = secrets.token_urlsafe(32)
    table().put_item(Item={"PK": "OAUTH", "SK": f"CODE#{code}", "client_id": client_id, "redirect_uri": redirect_uri,
                           "challenge": code_challenge, "household": household.upper(), "scope": scope,
                           "ttl": int(time.time()) + CODE_TTL})
    return code


def exchange(code: str, verifier: str, client_id: str, redirect_uri: str) -> dict[str, Any]:
    r = table().get_item(Key={"PK": "OAUTH", "SK": f"CODE#{code}"}).get("Item")
    if not r or r["client_id"] != client_id or r["redirect_uri"] != redirect_uri or int(r["ttl"]) < time.time():
        raise ValueError("invalid_grant")
    if _s256(verifier) != r["challenge"]:
        raise ValueError("invalid_grant")
    table().delete_item(Key={"PK": "OAUTH", "SK": f"CODE#{code}"})   # single use
    token = secrets.token_urlsafe(32)
    table().put_item(Item={"PK": "OAUTH", "SK": f"TOKEN#{token}", "household": r["household"], "scope": r["scope"],
                           "ttl": int(time.time()) + TOKEN_TTL})
    return {"access_token": token, "token_type": "Bearer", "expires_in": TOKEN_TTL, "scope": r["scope"]}


def household_for(token: str | None) -> str | None:
    if not token:
        return None
    r = table().get_item(Key={"PK": "OAUTH", "SK": f"TOKEN#{token}"}).get("Item")
    if not r or int(r["ttl"]) < time.time():
        return None
    return r["household"]


def metadata(issuer: str) -> dict[str, Any]:
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["household"],
    }
