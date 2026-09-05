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
    return board.build(profile, latest_message=store.latest_message(household),
                       checked_in=store.checkin_today(household) is not None)


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
