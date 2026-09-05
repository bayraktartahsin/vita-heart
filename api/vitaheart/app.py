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

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import __version__, board, config, store
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
    ext = "jpg" if body.content_type == "image/jpeg" else "png"
    key = f"{body.household.upper()}/{uuid.uuid4().hex}.{ext}"
    url = boto3.client("s3", region_name=config.REGION).generate_presigned_url(
        "put_object", Params={"Bucket": bucket, "Key": key, "ContentType": body.content_type}, ExpiresIn=600)
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
    obj = boto3.client("s3", region_name=config.REGION).get_object(Bucket=bucket, Key=body.key)
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
