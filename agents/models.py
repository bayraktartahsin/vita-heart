from __future__ import annotations

import os

REGION = os.environ.get("VITAHEART_REGION", "eu-north-1")

# Measured on 5 Sep 2026 in eu-north-1: Nova Lite 0.8 s, Claude Sonnet 4.5 2.0 s for a
# one-word reply; Claude Sonnet 5 is not enabled for this account.
READER_MODEL = os.environ.get("VITAHEART_READER_MODEL", "eu.amazon.nova-lite-v1:0")
WRITER_MODEL = os.environ.get("VITAHEART_WRITER_MODEL", "eu.anthropic.claude-sonnet-4-5-20250929-v1:0")
FALLBACK_MODEL = os.environ.get("VITAHEART_FALLBACK_MODEL", "eu.amazon.nova-pro-v1:0")
