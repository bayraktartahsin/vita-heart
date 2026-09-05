"""HTTP surface of Vita Heart.

Phase 1 routes:
  GET  /health
  GET  /board?household=CODE
  GET  /events?household=CODE&since=ISO      long-poll, returns within 20 s
  GET  /family/messages?household=CODE
  POST /family/messages   {household, author, text}
  POST /checkin           {household, by}
"""
from __future__ import annotations

import time

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import __version__, board, config, ring, store
from .meds import service as meds

app = FastAPI(title="Vita Heart API", version=__version__)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _profile_or_404(code: str) -> dict:
    p = store.get_profile(code)
    if not p:
        raise HTTPException(404, f"unknown household {code!r}")
    return p


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "vita-heart-api", "version": __version__, "table": config.TABLE}


@app.get("/board")
def get_board(household: str = Query(..., min_length=4, max_length=12)) -> dict:
    profile = _profile_or_404(household)
    b = board.build(profile, latest_message=store.latest_message(household),
                    checked_in=store.checkin_today(household) is not None)
    b["dueDoses"] = meds.due_doses(household, profile)
    b["clock"] = profile.get("clock") or {}
    return b


@app.get("/events")
def get_events(household: str = Query(..., min_length=4, max_length=12),
               since: str | None = None,
               wait: float = Query(config.LONG_POLL_SECONDS, ge=0, le=25)) -> dict:
    """Return events newer than `since`, holding the request open until one exists.

    `since` is the `ts` of the last event the client saw (or empty on first call).
    The response always carries `cursor`: pass it back unchanged.
    """
    _profile_or_404(household)
    deadline = time.monotonic() + wait
    cursor = since or store.now_iso()
    while True:
        items = store.events_since(household, cursor)
        if items or time.monotonic() >= deadline:
            events = [{"ts": i["ts"], "kind": i["kind"], "data": i.get("data", {})} for i in items]
            return {"events": events, "cursor": events[-1]["ts"] if events else cursor}
        time.sleep(config.LONG_POLL_INTERVAL)


class MessageIn(BaseModel):
    household: str = Field(min_length=4, max_length=12)
    author: str = Field(min_length=1, max_length=40)
    text: str = Field(min_length=1, max_length=280)


@app.get("/family/messages")
def messages(household: str = Query(..., min_length=4, max_length=12)) -> dict:
    _profile_or_404(household)
    return {"messages": [{"ts": m["ts"], "author": m["author"], "text": m["text"]}
                         for m in store.list_messages(household)]}


@app.post("/family/messages", status_code=201)
def post_message(body: MessageIn) -> dict:
    _profile_or_404(body.household)
    m = store.post_message(body.household, body.author, body.text)
    return {"ts": m["ts"], "author": m["author"], "text": m["text"]}


class CheckinIn(BaseModel):
    household: str = Field(min_length=4, max_length=12)
    by: str = Field(default="tv", max_length=20)


@app.post("/checkin", status_code=201)
def post_checkin(body: CheckinIn) -> dict:
    _profile_or_404(body.household)
    c = store.checkin(body.household, body.by)
    return {"ts": c["ts"], "by": c["by"]}


# ---- medicines (Phase 2) -----------------------------------------------------------

class UploadUrlIn(BaseModel):
    household: str = Field(min_length=4, max_length=12)
    content_type: str = Field(default="image/jpeg", pattern="^image/(jpeg|png)$")


@app.post("/meds/upload-url")
def upload_url(body: UploadUrlIn) -> dict:
    """A presigned PUT so the family's phone can send a box photo straight to S3."""
    import os
    import uuid

    import boto3

    _profile_or_404(body.household)
    bucket = os.environ.get("VITAHEART_BUCKET")
    if not bucket:
        raise HTTPException(503, "photo storage is not configured on this deployment")
    from botocore.config import Config

    ext = "jpg" if body.content_type == "image/jpeg" else "png"
    key = f"{body.household.upper()}/{uuid.uuid4().hex}.{ext}"
    # Regional endpoint + SigV4, otherwise the phone gets a 307 to the regional host and PUT fails.
    s3 = boto3.client("s3", region_name=config.REGION, endpoint_url=f"https://s3.{config.REGION}.amazonaws.com",
                      config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))
    url = s3.generate_presigned_url("put_object", Params={"Bucket": bucket, "Key": key, "ContentType": body.content_type}, ExpiresIn=600)
    return {"url": url, "key": key, "expiresIn": 600}


class ReadIn(BaseModel):
    household: str = Field(min_length=4, max_length=12)
    key: str = Field(min_length=3, max_length=200)


@app.post("/meds/read")
def read_photo(body: ReadIn) -> dict:
    """Read one uploaded photo: Reader, Identifier, Watchman, Scheduler. Returns the trace."""
    import os

    import boto3

    _profile_or_404(body.household)
    bucket = os.environ.get("VITAHEART_BUCKET")
    if not bucket or not body.key.startswith(body.household.upper() + "/"):
        raise HTTPException(400, "that photo does not belong to this household")
    try:
        obj = boto3.client("s3", region_name=config.REGION).get_object(Bucket=bucket, Key=body.key)
    except boto3.client("s3", region_name=config.REGION).exceptions.NoSuchKey:
        raise HTTPException(404, "that photo was never uploaded; try again")
    data = obj["Body"].read()
    fmt = "png" if body.key.endswith(".png") else "jpeg"
    return meds.read_photo(body.household, data, fmt, photo_key=body.key)


@app.get("/meds")
def list_meds(household: str = Query(..., min_length=4, max_length=12)) -> dict:
    _profile_or_404(household)
    return {"meds": store.list_meds(household)}


class ConfirmIn(BaseModel):
    household: str = Field(min_length=4, max_length=12)
    dose_id: str = Field(min_length=5, max_length=80)
    by: str = Field(default="tv", max_length=20)


@app.post("/doses/confirm", status_code=201)
def confirm_dose(body: ConfirmIn) -> dict:
    _profile_or_404(body.household)
    d = store.confirm_dose(body.household, body.dose_id, body.by)
    return {"id": body.dose_id, "ts": d["ts"], "by": d["by"]}


class ClockIn(BaseModel):
    household: str = Field(min_length=4, max_length=12)
    times: dict[str, str]   # slot -> "HH:MM" local


@app.post("/clock")
def set_clock(body: ClockIn) -> dict:
    """The household maps slots to its own clock, once, from the television."""
    _profile_or_404(body.household)
    bad = [s for s in body.times if s not in ("morning", "midday", "evening", "night")]
    if bad:
        raise HTTPException(422, f"unknown slot(s): {bad}")
    store.set_clock(body.household, body.times)
    return {"clock": body.times}


# ---- phone-facing pages ---------------------------------------------------------------

_WEB = Path(__file__).parent / "web"


@app.get("/cabinet", response_class=HTMLResponse)
def cabinet_page() -> str:
    """The family's phone page: photograph the boxes. Served by the API so there is one origin."""
    return (_WEB / "cabinet.html").read_text(encoding="utf-8")


# ---- heart sessions (Phase 3) ---------------------------------------------------------

class SessionStartIn(BaseModel):
    household: str = Field(min_length=4, max_length=12)
    source: str = Field(default="watch", pattern="^(watch|recorded|synthetic)$")   # the TV labels anything not "watch"


@app.post("/session/start", status_code=201)
def session_start(body: SessionStartIn) -> dict:
    """The television opens a session; the Watch (or the labelled replay) then posts heart rate into it."""
    import uuid

    _profile_or_404(body.household)
    sid = uuid.uuid4().hex[:10]
    store.start_session(body.household, sid, body.source)
    return {"id": sid, "source": body.source}


class HrIn(BaseModel):
    household: str = Field(min_length=4, max_length=12)
    session: str = Field(min_length=6, max_length=20)
    bpm: int = Field(ge=25, le=230)
    at: str | None = None


@app.post("/session/hr", status_code=202)
def session_hr(body: HrIn) -> dict:
    """One heart-rate sample from the wrist. Lands on the events channel within a second."""
    _profile_or_404(body.household)
    live = store.live_session(body.household)
    if not live or live["id"] != body.session:
        raise HTTPException(409, "that session is not live")
    store.add_hr(body.household, body.session, body.bpm, body.at)
    return {"ok": True}


class SessionFinishIn(BaseModel):
    household: str = Field(min_length=4, max_length=12)
    session: str = Field(min_length=6, max_length=20)
    summary: dict


@app.post("/session/finish")
def session_finish(body: SessionFinishIn) -> dict:
    _profile_or_404(body.household)
    store.finish_session(body.household, body.session, body.summary)
    return {"id": body.session, "state": "finished"}


@app.get("/session/live")
def session_live(household: str = Query(..., min_length=4, max_length=12)) -> dict:
    """What the Watch asks first: is the television waiting for me?"""
    _profile_or_404(household)
    live = store.live_session(household)
    return {"live": live}


class CoachIn(BaseModel):
    household: str = Field(min_length=4, max_length=12)
    numbers: dict


@app.post("/session/coach")
def session_coach(body: CoachIn) -> dict:
    """One encouraging line from the Coach agent for the current block. Never a claim, never a number it was not given."""
    import sys
    from pathlib import Path

    for cand in (Path(__file__).resolve().parents[1], Path(__file__).resolve().parents[2]):
        if (cand / "agents").is_dir() and str(cand) not in sys.path:
            sys.path.insert(0, str(cand))
    from agents import client

    _profile_or_404(body.household)
    try:
        line = client.coach_line(body.numbers)
    except Exception as e:  # noqa: BLE001  the session must never depend on the model
        line = ""
        return {"line": line, "fallback": True, "reason": type(e).__name__}
    return {"line": line, "fallback": False}


# ---- family page, summaries, trace, Night Watch (Phase 4) -----------------------------------

@app.get("/family", response_class=HTMLResponse)
def family_page() -> str:
    return (_WEB / "family.html").read_text(encoding="utf-8")


@app.get("/family/summary")
def family_summary(household: str = Query(..., min_length=4, max_length=12)) -> dict:
    _profile_or_404(household)
    return {"summary": store.latest_summary(household)}


@app.get("/trace")
def trace(household: str = Query(..., min_length=4, max_length=12)) -> dict:
    """Every agent tool call kept on the medicines, newest first: the agents thinking, legibly."""
    _profile_or_404(household)
    steps: list[dict] = []
    for m in store.list_meds(household):
        for st in m.get("trace") or []:
            steps.append({**st, "med": m.get("name")})
    steps.sort(key=lambda s: s.get("ts", ""), reverse=True)
    return {"steps": steps[:100]}


class NightRunIn(BaseModel):
    household: str = Field(min_length=4, max_length=12)
    notify: bool = True


@app.post("/night/run")
def night_run(body: NightRunIn) -> dict:
    """Run Night Watch now (the demo does not wait for 21:00)."""
    from .night import watch

    _profile_or_404(body.household)
    return watch.run_for(body.household, notify=body.notify)


# ---- Ring (Phase 4) ---------------------------------------------------------------------

@app.post("/ring/webhook")
async def ring_webhook(request: Request, household: str = Query(config.DEMO_HOUSEHOLD, min_length=4, max_length=12),
                       x_signature: str | None = Header(default=None)) -> dict:
    """Ring posts here. Verified with the app's HMAC key, answered within the 5 s Ring allows."""
    body = await request.body()
    if not ring.verify(body, x_signature, ring.hmac_key()):
        raise HTTPException(401, "signature did not verify")
    _profile_or_404(household)
    import json
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(400, "body is not JSON")
    return ring.ingest(household, payload)


@app.get("/signals")
def signals(household: str = Query(..., min_length=4, max_length=12), hours: int = Query(24, ge=1, le=168)) -> dict:
    from datetime import datetime, timedelta, timezone

    _profile_or_404(household)
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="microseconds")
    return {"signals": [{"ts": s["ts"], "kind": s["kind"], "device": s.get("device"), "value": s.get("value")}
                        for s in store.signals_since(household, since)]}


# ---- Alexa+: OAuth 2.1 PKCE + MCP (Phase 5) ---------------------------------------------------

import asyncio  # noqa: E402
import sys as _sys  # noqa: E402
for _cand in (Path(__file__).resolve().parents[2],):
    if (_cand / "alexa").is_dir() and str(_cand) not in _sys.path:
        _sys.path.insert(0, str(_cand))
from alexa import oauth as _oauth  # noqa: E402
from alexa import server as _mcp  # noqa: E402
from fastapi.responses import JSONResponse, RedirectResponse  # noqa: E402
from urllib.parse import urlencode  # noqa: E402


def _issuer(request: Request) -> str:
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost"
    scheme = request.headers.get("x-forwarded-proto") or ("https" if "amazonaws" in host else request.url.scheme)
    return f"{scheme}://{host}"


@app.get("/.well-known/oauth-authorization-server")
def oauth_metadata(request: Request) -> dict:
    return _oauth.metadata(_issuer(request))


@app.get("/.well-known/oauth-protected-resource")
def protected_resource(request: Request) -> dict:
    iss = _issuer(request)
    return {"resource": f"{iss}/mcp", "authorization_servers": [iss], "scopes_supported": ["household"], "bearer_methods_supported": ["header"]}


@app.get("/oauth/authorize", response_class=HTMLResponse)
def oauth_authorize(request: Request, client_id: str, redirect_uri: str, code_challenge: str, state: str = "",
                    code_challenge_method: str = "S256", scope: str = "household", response_type: str = "code") -> str:
    """The consent page: the household types the code shown on its television. No Amazon password anywhere."""
    if response_type != "code":
        raise HTTPException(400, "response_type must be code")
    q = urlencode({"client_id": client_id, "redirect_uri": redirect_uri, "code_challenge": code_challenge,
                   "code_challenge_method": code_challenge_method, "state": state, "scope": scope})
    return f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Vita Heart · Connect</title><body style="font:18px system-ui;background:#f6f2ea;color:#1a1f26;margin:0">
<main style="max-width:480px;margin:0 auto;padding:32px 20px"><h1 style="font-size:26px">Connect Alexa+ to Vita Heart</h1>
<p>Type the household code shown on the television. This lets Alexa+ read today's board and confirm medicines on it.</p>
<form method=post action="/oauth/approve?{q}"><input name=household maxlength=12 required autocapitalize=characters
 style="font:22px system-ui;letter-spacing:3px;padding:12px;border-radius:12px;border:1px solid #d8d1c4;width:100%">
<button style="margin-top:14px;font:700 18px system-ui;padding:14px 20px;border:0;border-radius:12px;background:#f2a93b;width:100%">Allow</button></form></main>"""


@app.post("/oauth/approve")
async def oauth_approve(request: Request, client_id: str, redirect_uri: str, code_challenge: str, state: str = "",
                        code_challenge_method: str = "S256", scope: str = "household"):
    form = await request.form()
    household = str(form.get("household", "")).strip().upper()
    if not store.get_profile(household):
        raise HTTPException(400, "unknown household code")
    try:
        code = _oauth.issue_code(client_id, redirect_uri, code_challenge, code_challenge_method, household, scope)
    except ValueError as e:
        raise HTTPException(400, str(e))
    sep = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(f"{redirect_uri}{sep}{urlencode({'code': code, 'state': state})}", status_code=302)


@app.post("/oauth/token")
async def oauth_token(request: Request):
    form = await request.form()
    if form.get("grant_type") != "authorization_code":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)
    try:
        return _oauth.exchange(str(form.get("code", "")), str(form.get("code_verifier", "")),
                               str(form.get("client_id", "")), str(form.get("redirect_uri", "")))
    except ValueError:
        return JSONResponse({"error": "invalid_grant"}, status_code=400)


class _McpAuth:
    """Bearer token in, household out. Anonymous: a bare 401, exactly as the Alexa+ toolkit specifies.

    Dispatches at the ASGI layer (not a Starlette sub-mount) so `/mcp` works without a
    trailing-slash redirect, which MCP clients do not follow.
    """

    def __init__(self, inner, fallback):
        self.inner = inner
        self.fallback = fallback
        self._ready = None
        self._task = None
        self._loop = None

    async def _runner(self, manager, ready):
        # Hold the session manager open in one long-lived task; entering it inside a request
        # task and leaving it in another breaks anyio's cancel scopes.
        try:
            async with manager.run():
                ready.set()
                await asyncio.Event().wait()
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger("vitaheart.mcp").exception("MCP session manager stopped")
            ready.set()   # never leave a request waiting forever

    async def _ensure_started(self):
        # FastMCP's session manager normally starts with the Starlette lifespan. This app is
        # dispatched by hand and runs on Lambda with lifespans off, so start it on first use.
        loop = asyncio.get_running_loop()
        if self._ready is None or self._loop is not loop:   # first use, or a new event loop (tests, reloads)
            # A StreamableHTTPSessionManager runs once per instance, so each loop gets a fresh app + manager.
            self._loop = loop
            srv = _mcp.build_server()
            self.inner = srv.streamable_http_app()
            self._ready = asyncio.Event()
            self._task = loop.create_task(self._runner(srv.session_manager, self._ready))
        await self._ready.wait()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not (scope["path"] == "/mcp" or scope["path"].startswith("/mcp/")):
            return await self.fallback(scope, receive, send)
        await self._ensure_started()
        scope = dict(scope)
        scope["path"] = "/" + scope["path"][len("/mcp"):].lstrip("/")
        scope["raw_path"] = scope["path"].encode()
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        auth = headers.get("authorization", "")
        token = auth[7:] if auth.lower().startswith("bearer ") else None
        household = _oauth.household_for(token)
        if not household:
            await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})
            return
        tok = _mcp.current_household.set(household)
        try:
            await self.inner(scope, receive, send)
        except Exception:  # noqa: BLE001  log the real cause; the client only sees a 500
            import logging
            logging.getLogger("vitaheart.mcp").exception("MCP request failed")
            raise
        finally:
            _mcp.current_household.reset(tok)


# The deployable ASGI app: /mcp goes to the MCP server behind bearer auth, everything else to FastAPI.
asgi = _McpAuth(_mcp.asgi_app, app)
