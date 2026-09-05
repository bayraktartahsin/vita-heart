"""Call the fleet where it runs.

When VITAHEART_AGENT_ARN is set (the API on Lambda), the Bedrock AgentCore
Runtime does the work. Otherwise (local development, tests) the same functions
run in-process. One code path for the agents; two places it can run.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any

REGION = os.environ.get("VITAHEART_REGION", "eu-north-1")


def agent_arn() -> str | None:
    return os.environ.get("VITAHEART_AGENT_ARN") or None


def _invoke_runtime(payload: dict[str, Any], session_id: str | None = None) -> dict[str, Any]:
    import boto3

    client = boto3.client("bedrock-agentcore", region_name=REGION)
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn(),
        runtimeSessionId=session_id or uuid.uuid4().hex + uuid.uuid4().hex[:8],   # >= 33 chars required
        payload=json.dumps(payload).encode("utf-8"),
        contentType="application/json", accept="application/json",
    )
    body = resp["response"].read() if hasattr(resp.get("response"), "read") else resp.get("response")
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8")
    return json.loads(body) if body else {}


def read_boxes(readings: list[dict[str, Any]], session_id: str | None = None) -> dict[str, Any]:
    if agent_arn():
        out = _invoke_runtime({"action": "read", "readings": readings}, session_id)
        out["ran_on"] = "agentcore"
        return out
    from . import run
    out = run.read_boxes(readings)
    out["ran_on"] = "in-process"
    return out


def pharmacist_question(finding: dict[str, Any]) -> str:
    if agent_arn():
        return _invoke_runtime({"action": "question", "finding": finding}).get("question", "")
    from . import run
    return run.write_pharmacist_question(finding)


def family_line(facts: dict[str, Any]) -> str:
    if agent_arn():
        return _invoke_runtime({"action": "family_line", "facts": facts}).get("line", "")
    from . import run
    return run.write_family_line(facts)


def coach_line(numbers: dict[str, Any]) -> str:
    if agent_arn():
        return _invoke_runtime({"action": "coach", "numbers": numbers}).get("line", "")
    from . import run
    return run.coach_line(numbers)
