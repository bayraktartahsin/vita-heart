"""OAuth PKCE + MCP over Streamable HTTP, against the real ASGI app on a local port."""
import base64
import hashlib
import secrets
import socket
import threading
import time

import httpx
import pytest
import uvicorn


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture
def server(ddb):
    from alexa import oauth
    from vitaheart import seed, app as appmod
    oauth.reset_for_tests()
    seed.main()
    port = free_port()
    cfg = uvicorn.Config(appmod.asgi, host="127.0.0.1", port=port, log_level="error")
    srv = uvicorn.Server(cfg)
    t = threading.Thread(target=srv.run, daemon=True)
    t.start()
    for _ in range(50):
        try:
            httpx.get(f"http://127.0.0.1:{port}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    t.join(timeout=5)


def pkce_token(base: str) -> str:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    redirect = "https://alexa.example/callback"
    with httpx.Client(follow_redirects=False) as c:
        meta = c.get(f"{base}/.well-known/oauth-authorization-server").json()
        assert meta["code_challenge_methods_supported"] == ["S256"]
        page = c.get(f"{base}/oauth/authorize", params={"client_id": "vita-heart-alexa", "redirect_uri": redirect,
                                                        "code_challenge": challenge, "state": "xyz"})
        assert page.status_code == 200 and "household code" in page.text
        r = c.post(f"{base}/oauth/approve", params={"client_id": "vita-heart-alexa", "redirect_uri": redirect,
                                                   "code_challenge": challenge, "state": "xyz"}, data={"household": "AHMET1"})
        assert r.status_code == 302 and r.headers["location"].startswith(redirect)
        code = httpx.URL(r.headers["location"]).params["code"]
        tok = c.post(f"{base}/oauth/token", data={"grant_type": "authorization_code", "code": code, "code_verifier": verifier,
                                                  "client_id": "vita-heart-alexa", "redirect_uri": redirect})
        assert tok.status_code == 200, tok.text
        # single use
        assert c.post(f"{base}/oauth/token", data={"grant_type": "authorization_code", "code": code, "code_verifier": verifier,
                                                   "client_id": "vita-heart-alexa", "redirect_uri": redirect}).status_code == 400
        return tok.json()["access_token"]


def test_anonymous_mcp_call_gets_a_bare_401(server):
    r = httpx.post(f"{server}/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert r.status_code == 401
    assert "www-authenticate" not in {k.lower() for k in r.headers}


def test_pkce_then_tools_over_streamable_http(server):
    import asyncio

    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    token = pkce_token(server)

    async def go():
        async with streamablehttp_client(f"{server}/mcp", headers={"Authorization": f"Bearer {token}"}) as (r, w, _):
            async with ClientSession(r, w) as s:
                init = await s.initialize()
                assert init.serverInfo.name == "Vita Heart"
                tools = {t.name for t in (await s.list_tools()).tools}
                assert tools == {"get_today_board", "confirm_medication", "start_heart_session", "get_family_status", "request_refill"}
                t0 = time.perf_counter()
                res = await s.call_tool("get_today_board", {})
                latency = time.perf_counter() - t0
                assert res.structuredContent["greeting"].endswith("Ahmet")
                assert latency < 0.5, f"{latency:.3f}s"
                miss = await s.call_tool("confirm_medication", {"name": "Coraspin"})
                assert miss.structuredContent["confirmed"] is False
                fam = await s.call_tool("get_family_status", {})
                assert fam.structuredContent["checkedInToday"] is False
                card = await s.read_resource("vita-heart://board/AHMET1")
                assert "Ahmet" in card.contents[0].text

    asyncio.run(go())
