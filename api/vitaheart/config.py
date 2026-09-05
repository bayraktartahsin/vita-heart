from __future__ import annotations

import os

REGION = os.environ.get("VITAHEART_REGION", "eu-north-1")
TABLE = os.environ.get("VITAHEART_TABLE", "vitaheart")

# How long /events may hold a request open. API Gateway's HTTP API cuts the
# connection at 30 s; 20 s leaves room for the Lambda to return cleanly.
LONG_POLL_SECONDS = float(os.environ.get("VITAHEART_LONG_POLL_SECONDS", "20"))
LONG_POLL_INTERVAL = float(os.environ.get("VITAHEART_LONG_POLL_INTERVAL", "0.3"))

# The household used by the demo and by the judges' testing instructions.
DEMO_HOUSEHOLD = "AHMET1"
