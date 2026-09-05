"""One conversational turn of the simulated Alexa+ surface.

    utterance -> Claude on Bedrock chooses one of the MCP tools (or none)
              -> the tool runs through the same functions the MCP server exposes
              -> Claude phrases one short spoken reply from the tool result
              -> the board card resource is attached when it helps

The tool schemas handed to the model are the MCP server's own (list_tools), so
the simulation cannot drift from what Alexa+ would see.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

import boto3

from . import server as srv

MODEL = os.environ.get("VITAHEART_WRITER_MODEL", "eu.anthropic.claude-sonnet-4-5-20250929-v1:0")
REGION = os.environ.get("VITAHEART_REGION", "eu-north-1")

SYSTEM = ("You are Alexa+ speaking to a family that uses Vita Heart, the health room on an older parent's television. "
          "Decide whether one of the tools answers the request; call at most one tool. Then reply in one or two short spoken "
          "sentences, warm and plain, using only what the tool returned. Never give medical advice. If nothing fits, say what you can do.")


def _tool_specs(fastmcp) -> list[dict[str, Any]]:
    tools = asyncio.run(fastmcp.list_tools())
    return [{"toolSpec": {"name": t.name, "description": t.description or t.name,
                          "inputSchema": {"json": t.inputSchema}}} for t in tools]


def _call(fastmcp, name: str, args: dict[str, Any]) -> Any:
    res = asyncio.run(fastmcp.call_tool(name, args))
    # FastMCP returns (content, structured) or a list of content blocks depending on version.
    if isinstance(res, tuple) and len(res) == 2 and isinstance(res[1], dict):
        return res[1]
    blocks = res[0] if isinstance(res, tuple) else res
    for b in blocks:
        text = getattr(b, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
    return {}


def turn(household: str, utterance: str) -> dict[str, Any]:
    fastmcp = srv.build_server()
    tok = srv.current_household.set(household)
    try:
        br = boto3.client("bedrock-runtime", region_name=REGION)
        specs = _tool_specs(fastmcp)
        msgs = [{"role": "user", "content": [{"text": utterance}]}]
        t0 = time.perf_counter()
        first = br.converse(modelId=MODEL, system=[{"text": SYSTEM}], messages=msgs,
                            toolConfig={"tools": specs}, inferenceConfig={"maxTokens": 300, "temperature": 0.2})
        out = first["output"]["message"]
        tool_name, tool_ms, result, card = None, None, None, None
        uses = [c["toolUse"] for c in out["content"] if "toolUse" in c]
        if uses:
            u = uses[0]
            tool_name = u["name"]
            t1 = time.perf_counter()
            result = _call(fastmcp, tool_name, u.get("input") or {})
            tool_ms = int((time.perf_counter() - t1) * 1000)
            msgs.append(out)
            msgs.append({"role": "user", "content": [{"toolResult": {"toolUseId": u["toolUseId"],
                                                                      "content": [{"json": result if isinstance(result, dict) else {"result": result}}]}}]})
            second = br.converse(modelId=MODEL, system=[{"text": SYSTEM}], messages=msgs,
                                 toolConfig={"tools": specs}, inferenceConfig={"maxTokens": 200, "temperature": 0.2})
            speech = " ".join(c.get("text", "") for c in second["output"]["message"]["content"] if "text" in c).strip()
            if tool_name in ("get_today_board", "confirm_medication", "start_heart_session"):
                card = asyncio.run(fastmcp.read_resource(f"vita-heart://board/{household}"))[0].content
        else:
            speech = " ".join(c.get("text", "") for c in out["content"] if "text" in c).strip()
        return {"speech": speech, "tool": tool_name, "ms": tool_ms, "result": result, "card": card,
                "model": MODEL, "totalMs": int((time.perf_counter() - t0) * 1000)}
    finally:
        srv.current_household.reset(tok)
