"""Lambda entry point. Two kinds of event.

  An HTTP request from API Gateway   -> the FastAPI app, via Mangum.
  {"source": "schedule"} (EventBridge) -> Night Watch for every household.
"""
from __future__ import annotations

import logging

from mangum import Mangum

from .app import app

log = logging.getLogger("vitaheart.lambda")
_http = Mangum(app, lifespan="off")


def handler(event, context):
    if isinstance(event, dict) and event.get("source") in ("schedule", "aws.events"):
        from .night import watch
        out = watch.run_all()
        log.info("night watch ran for %d household(s)", len(out))
        return {"ran": len(out)}
    return _http(event, context)
