# Testing instructions (for judges)

Nothing to install for the cloud side. The television part needs the Vega Virtual Device
(free, macOS/Linux) or the video.

## 1. Live cloud, no setup
- Board: https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com/board?household=AHMET1
- Family page (phone-sized): https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com/family?household=AHMET1 (write a reply: it appears on the TV within a second)
- Add boxes (phone camera): https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com/cabinet?household=AHMET1
- Agent trace: https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com/trace?household=AHMET1
- Night Watch on demand: `curl -X POST .../night/run -H 'content-type: application/json' -d '{"household":"AHMET1","notify":false}'`

## 2. Alexa+ (MCP)
- Simulated surface: https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com/alexa-sim . First message opens the consent page; type the household code `AHMET1`. Then speak (Chrome) or type: "How is Dad doing today?", "Tell Vita Heart I took the morning Coraspin", "Order a refill of his Glifor".
- Raw MCP: `POST /mcp` without a token returns 401 with no WWW-Authenticate (the Alexa+ contract). With MCP Inspector: OAuth metadata at `/.well-known/oauth-authorization-server`, client id `vita-heart-alexa`, PKCE S256, scope `household`.

## 3. Television
```bash
cd tv && npm install && npm run build:debug && vega run-app build/aarch64-debug/vitahearttv_aarch64.vpkg
```
The app opens on household AHMET1. Arrows + OK. "I'm up" → the family page shows the tick. "Show me" → Medication Moment → "I took it". "Set my times" → the clock. "Start with my Watch" → Heart Session; without a Watch, run `python scripts/replay_hr.py --synthetic` after starting a *synthetic* session (the TV labels it "test signal").

## 4. Ring
`python scripts/ring_simulate.py night` posts signed synthetic webhooks (door at 03:10, hall under 18 C); Night Watch turns them into the family sentence. Bad signatures are refused (`tests/test_ring.py`).

## 5. Tests
`pytest -q tests` (37) and `cd tv && npm test` (15). Live tests: `VITAHEART_LIVE=1`.
