"""Vita Heart as an Alexa+ add-on: five tools and one card, over MCP 2025-11-25.

Alexa+ (or the simulated surface) asks; the television reacts within a second
because every mutation lands on the household's events channel. Nothing here
calls a model: the round trip is DynamoDB only, well inside the 500 ms budget.
"""
from __future__ import annotations

import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

for cand in (Path(__file__).resolve().parents[1] / "api",):
    if str(cand) not in sys.path:
        sys.path.insert(0, str(cand))

from vitaheart import board, store  # noqa: E402
from vitaheart.meds import service as meds  # noqa: E402

# The household is set per request by the auth wrapper in app.py (from the bearer token).
current_household: ContextVar[str] = ContextVar("current_household", default="AHMET1")

def build_server() -> FastMCP:
    """A fresh server (and therefore a fresh session manager) per event loop.

    The SDK's StreamableHTTPSessionManager runs once per instance; the API builds one
    of these per loop (tests, reloads) rather than fighting that rule.
    """
    server = FastMCP(
        "Vita Heart",
        instructions=("Vita Heart is the health room on an older parent's television. Tools read today's board, "
                      "confirm a medicine was taken, start a seated heart session, report family status and "
                      "prepare a refill request. Never give medical advice; relay what the television knows."),
        stateless_http=True,
        json_response=True,
        streamable_http_path="/",
        # The SDK's DNS-rebinding guard allows only localhost Host headers; behind API Gateway
        # every request would be 421. Bearer tokens (OAuth 2.1 PKCE) guard this endpoint instead.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


    def _hh() -> str:
        return current_household.get()


    @server.tool()
    def get_today_board() -> dict[str, Any]:
        """Today's board for the household: greeting, doses due (with confirmation state), last family message, check-in."""
        code = _hh()
        profile = store.get_profile(code) or {}
        b = board.build(profile, latest_message=store.latest_message(code), checked_in=store.checkin_today(code) is not None)
        b["dueDoses"] = meds.due_doses(code, profile)
        return b


    @server.tool()
    def confirm_medication(name: str, slot: str = "") -> dict[str, Any]:
        """Mark a medicine as taken by name (and optionally slot: morning, midday, evening, night). Updates the television."""
        code = _hh()
        profile = store.get_profile(code) or {}
        due = meds.due_doses(code, profile)
        want = name.strip().lower()
        matches = [d for d in due if (d.get("name") or "").lower().startswith(want) and (not slot or d["slot"] == slot) and not d["confirmed"]]
        if not matches:
            return {"confirmed": False, "reason": f"nothing open called '{name}'" + (f" for {slot}" if slot else ""),
                    "open": [f"{d.get('name')} ({d['slot']})" for d in due if not d["confirmed"]]}
        d = matches[0]
        store.confirm_dose(code, d["id"], by="alexa")
        return {"confirmed": True, "name": d.get("name"), "slot": d["slot"], "doseId": d["id"]}


    @server.tool()
    def start_heart_session(source: str = "watch") -> dict[str, Any]:
        """Ask the television to begin the ten-minute seated session (source: watch or recorded)."""
        code = _hh()
        if store.live_session(code):
            return {"started": False, "reason": "a session is already live"}
        import uuid

        sid = uuid.uuid4().hex[:10]
        store.start_session(code, sid, source if source in ("watch", "recorded", "synthetic") else "watch")
        store.emit(code, "board", {"startSession": sid})
        return {"started": True, "session": sid}


    @server.tool()
    def get_family_status() -> dict[str, Any]:
        """The latest Night Watch summary and today's check-in, for a family member asking Alexa."""
        code = _hh()
        s = store.latest_summary(code)
        return {"checkedInToday": store.checkin_today(code) is not None,
                "summary": (s or {}).get("text"), "summaryDay": (s or {}).get("day"),
                "signals": [x.get("note") for x in (s or {}).get("signals", [])]}


    @server.tool()
    def request_refill(name: str) -> dict[str, Any]:
        """Prepare a refill request for a medicine. Returns a checkout intent for Alexa+ to confirm; no payment is taken here."""
        code = _hh()
        ms = [m for m in store.list_meds(code) if (m.get("name") or "").lower().startswith(name.strip().lower())]
        if not ms:
            return {"prepared": False, "reason": f"no medicine called '{name}' on the television"}
        m = ms[0]
        intent = {"prepared": True, "item": f"{m.get('name')} {m.get('strength') or ''}".strip(),
                  "rxcui": (m.get("identity") or {}).get("rxcui"), "quantity": 1,
                  "checkout": {"type": "pharmacy-pickup", "status": "awaiting-confirmation", "note": "Confirmation happens in Alexa+; the pharmacy fulfils."}}
        store.emit(code, "board", {"refill": intent["item"]})
        return intent


    @server.resource("vita-heart://board/{household}")
    def board_card(household: str) -> str:
        """An MCP App card: the board as small HTML for a conversation surface."""
        code = household.upper()
        profile = store.get_profile(code) or {}
        b = board.build(profile, latest_message=store.latest_message(code), checked_in=store.checkin_today(code) is not None)
        due = meds.due_doses(code, profile)
        rows = "".join(f"<li>{'✓' if d['confirmed'] else '○'} {d.get('name')} · {d['slot']}</li>" for d in due) or "<li>Nothing due</li>"
        return (f"<div style='font:16px system-ui;padding:12px;border-radius:12px;background:#1a1f26;color:#f4f1ea'>"
                f"<b>{b['greeting']}</b><ul style='margin:8px 0 0 16px;padding:0'>{rows}</ul>"
                f"<div style='opacity:.7;margin-top:8px'>{'Said I am up' if b['checkedInToday'] else 'Not checked in yet'} · "
                f"{datetime.now(timezone.utc):%H:%M} UTC</div></div>")


    return server


server = build_server()          # module-level instance for tooling and inspection
asgi_app = server.streamable_http_app()
