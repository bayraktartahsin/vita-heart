"""Lambda entry point: the same FastAPI app, through Mangum."""
from __future__ import annotations

from mangum import Mangum

from .app import app

handler = Mangum(app, lifespan="off")
