"""The fleet, hosted on Amazon Bedrock AgentCore Runtime. Lives at the repo root so
`agents` and `api/vitaheart` resolve inside the container the same way they do locally.

Payloads:
  {"action": "read", "readings": [BoxReading...]}     -> meds + trace + what the agents said
  {"action": "question", "finding": {...}}            -> the Scribe's pharmacist question
  {"action": "family_line", "facts": {...}}           -> one calm sentence for the family
  {"action": "coach", "numbers": {...}}               -> one line for the session screen
"""
from __future__ import annotations

import sys
from pathlib import Path

from bedrock_agentcore import BedrockAgentCoreApp

sys.path.insert(0, str(Path(__file__).resolve().parent / "api"))  # vitaheart.meds.schedule
from agents import run  # noqa: E402

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict, context=None) -> dict:
    payload = payload or {}
    action = payload.get("action", "read")
    if action == "question":
        return {"question": run.write_pharmacist_question(payload.get("finding") or {})}
    if action == "family_line":
        return {"line": run.write_family_line(payload.get("facts") or {})}
    if action == "coach":
        return {"line": run.coach_line(payload.get("numbers") or {})}
    return run.read_boxes(payload.get("readings") or [])


if __name__ == "__main__":
    app.run()
