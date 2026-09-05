# Vita Heart. Master plan

**One line:** The television an older parent already watches becomes their health room.

**Entry:** Build, Ship, Shape: Amazon Developer Hackathon. Primary track Fire TV (Vega OS). Second track entry Alexa+. Mini challenges AWS Builder and Open Source. Deadline Fri 23 Oct 2026 12:00 PDT (22:00 Istanbul). Internal hard stop: Thu 22 Oct 20:00 Istanbul.

**Publisher:** Tahsin Bayraktar, Graviti Labs, info@gravitilabs.com. Repo github.com/bayraktartahsin/vita-heart (Apache-2.0).

---

## 0. Why this wins (the judging map)

The rules give an answer key: "Judges should distinguish creative ideas from obvious ones", with examples per track. Every feature below exists to hit a named "creative" example or a named priority category. Nothing else ships.

| Criterion (25% each) | What the judge must see in 3 minutes | Where it lives |
|---|---|---|
| Tech Implementation | Native Vega OS app on the Vega simulator, real device APIs (TV focus engine, D-pad, 10-foot rendering, live SSE updates), Strands agents on AgentCore, MCP server on spec 2025-11-25 Streamable HTTP, Ring webhooks with HMAC verification | tv/, agents/, api/, mcp/ |
| Design | One coherent product: Morning Board, Medication Moment, Heart Session, Family. Typography for a 72-year-old at 3 metres. Every screen works with four arrows and OK. | tv/src/design, tv/src/screens |
| Potential Impact | Adults 65+ watch more TV than any age group and their children live elsewhere. Fire TV Appstore listing draft. Backed by Vita, a shipping App Store health app. | docs/APPSTORE-LISTING.md, README |
| Quality of the Idea | Fire TV "creative" examples hit: adapts to household patterns (Night Watch), fitness with a real body signal on the TV (Heart Session), multi-modal voice + D-pad + visual in one flow (Alexa+ tells the TV). Ring "creative": caretaking, non-security, sensors. Alexa+ "creative": agentic, stateful across sessions, purchasing (refill intent), MCP Apps card. AWS "creative": Bedrock + AgentCore + Strands pipeline. | everywhere |
| Friction-log bonus (+10%) | 12+ entries written as engineers write them | docs/FRICTION-LOG.md |

Kill-questions, answered: Vega OS is load-bearing (the TV is the product). Non-expert understands it in 3 minutes (a father, a television, a daughter's phone). Wow moment: his real heart rate drawn on his television during a seated workout, and the coach shortening the set. Shippable: yes, with degrade paths written below.

---

## 1. The story the demo tells (one storyline exercises every feature)

Ahmet, 72, Istanbul, lives alone, Fire TV in the living room. Selin, his daughter, lives in Ankara, has Vita on her iPhone.

1. **07:40. Morning Board.** TV wakes to "Günaydın Ahmet" in large type: two tablets due at 08:00 (boxes photographed once by Selin), resting heart rate from his Watch last night, one line from Selin, a big "I'm up" button. He presses OK. Selin's phone gets a quiet tick.
2. **08:00. Medication Moment.** The two boxes appear as photos with plain names. He confirms with OK. One box was recalled last month: the TV does not diagnose; it shows the question to ask the pharmacist (the VitaCabinet rule).
3. **Alexa+.** He says "Alexa, tell Vita Heart I took the evening ones already." Alexa+ calls our MCP tool; the TV updates within a second. Voice, remote and screen in one flow.
4. **10:00. Heart Session.** "Ten minutes, seated." His Watch streams heart rate; the number and a live trace are on the television; the coach shortens the second set when recovery lags. He never touches a phone.
5. **The front door.** Ring sensors at the door and in the hall feed Night Watch: door opened at 03:10, no motion by 10:00, hall at 16 degrees. Nothing alarms; the TV shows a calm card and Selin gets one sentence at 21:00.
6. **21:00. Family summary.** Night Watch (Strands agents on AgentCore, EventBridge) writes one plain sentence to Selin: "Dad took both morning tablets, did 9 of 10 minutes with heart rate in range, the door was quiet." She replies from Vita; it appears on his TV tomorrow morning.

Video order (Setup, Watch, Payoff, 2:50): 1 to 6 in that order, unedited, English narration, no music.

---

## 2. Top-level design

```
┌──────────────── LIVING ROOM ────────────────┐   ┌──────────── DAUGHTER ────────────┐
│ Fire TV (Vega OS)  ── Vita Heart TV app      │   │ iPhone: Vita (existing app)      │
│  Morning Board · Medication Moment ·         │   │  + web page /family (this repo)  │
│  Heart Session · Family · Pairing            │   └──────────────┬───────────────────┘
│  ▲ long-poll /events  ▼ HTTPS JSON                 │                  │
└───────┬─────────────────────────────────────┘                  │
        │                    ┌───────────── FRONT DOOR ──────────┐│
        │                    │ Ring doorbell + sensors (sandbox) ││
        │                    │  webhooks, HMAC-SHA256            ││
        │                    └──────────────┬────────────────────┘│
        ▼                                   ▼                     ▼
┌──────────────────────────── AWS eu-north-1 ─────────────────────────────────┐
│ API Gateway (HTTP) ─► Lambda: FastAPI "Vita Heart API"                      │
│   /board /meds /meds/confirm /session /session/hr /events(long-poll) /ring/webhook│
│   /mcp (Streamable HTTP, MCP 2025-11-25, OAuth 2.1 PKCE)  /alexa-sim (web)  │
│ DynamoDB `vitaheart` (household, meds, sessions, signals, summaries, trace)  │
│ Bedrock AgentCore Runtime ─► Strands agents:                                │
│   Reader (Nova Lite vision) · Identifier (RxNorm) · Watchman (openFDA)      │
│   Coach (zones + one sentence) · Night Watch (patterns) · Scribe (no tools) │
│ EventBridge 21:00 ─► Night Watch ─► SNS email to family                     │
│ CloudWatch + AgentCore observability                                        │
└─────────────────────────────────────────────────────────────────────────────┘
        ▲                                   ▲
┌───────┴────────┐               ┌──────────┴───────────┐
│ Apple Watch    │               │ Alexa+ (simulated    │
│ VitaHeartWatch │               │ surface + real MCP)  │
│ HKLiveWorkout  │               │ browser voice → tool │
│ HR → /session  │               └──────────────────────┘
└────────────────┘
```

### 2.1 TV app (tv/)
- Vega OS, React Native 0.83, TypeScript, `@amazon-devices/react-native-kepler` for TVFocusGuideView and TV event handling. No third-party UI kit; a small design system in `tv/src/design` (tokens: type scale 36/48/72/120 px, 3-metre contrast, warm palette, focus ring 6 px).
- Screens: `MorningBoard`, `MedicationMoment`, `HeartSession`, `Family`, `Pairing`, `NightWatchCard` (overlay). Navigation is a 4-tab rail plus overlays; every action reachable with arrows + OK + Back.
- Data: `tv/src/api` (fetch wrapper with household code), `tv/src/live` (long-poll client with backoff and a visible "live" indicator). All live updates (HR samples, Alexa+ actions, Ring signals, family replies) arrive on one `/events` channel.
- Voice on the TV: honest. The remote's microphone is not available to third-party Vega apps in the simulator, so voice enters via Alexa+ and is shown arriving on the TV. No fake mic button.
- Tests: jest + @testing-library/react-native for screens and the session engine; snapshot of the board with seeded data.

### 2.2 API (api/)
- Python 3.12, FastAPI, Mangum adapter, deployed to Lambda behind API Gateway HTTP API (the pattern that worked for VitaCabinet in this account; Lambda Function URLs return 403 here).
- DynamoDB single table `vitaheart`, PK/SK design: `HH#<code>` household; `MED#`, `DOSE#<date>`, `SESSION#<ts>`, `HR#<session>#<ts>`, `SIGNAL#<ts>` (Ring), `SUMMARY#<date>`, `TRACE#<job>#<seq>`, `MSG#<ts>` (family).
- Live channel: `/events?household=&since=` is a long-poll. The Lambda checks DynamoDB every 300 ms for up to 20 s and returns as soon as something new exists; the TV reconnects immediately. API Gateway plus Lambda cannot stream responses (Function URLs, which can, return 403 in this account), so SSE is deliberately not used. Documented as a friction item, not hidden.
- Security: household code + device token; Ring webhook HMAC-SHA256 verification; MCP OAuth 2.1 PKCE with a static demo client; no secrets in the repo, all in Secrets Manager / Lambda env.

### 2.3 Agents (agents/)
- Strands Agents SDK on Amazon Bedrock. Vendored and credited from VitaCabinet (Apache-2.0): `rxnorm.py`, `fda.py`, the confidence-decay `cabinet.py`, the tool-ledger pattern.
- Reader: Nova Lite reads box photos to name + strength (reads, never identifies). Identifier: RxNorm. Watchman: openFDA live recalls. Coach: deterministic zone engine (age-based max HR, seated protocol) + one sentence per interval from the model. Night Watch: rules over Ring signals and dose history + model-written summary. Scribe: one sentence per finding, holds no tools (the safety model).
- Hosted on AgentCore Runtime (`agentcore deploy`), invoked from the API. Every tool call is written to `TRACE#` so the TV's Family screen and the web `/trace` page can show the agents thinking.

### 2.4 Watch (watch/)
- `VitaHeartWatch`: minimal SwiftUI watchOS app. HKWorkoutSession + HKLiveWorkoutBuilder, heart rate every ~5 s, POST to `/session/hr` with the household code. Pairing by 6-character code shown on the TV. Built with xcodegen (project.yml committed; entitlements checked on the signed binary, see the xcodegen trap note).
- Degrade path: `scripts/replay_hr.py` replays a real recorded session exported from HealthKit (the founder's own), and the TV labels it "recorded session". Never a synthetic sine wave.

### 2.5 Ring (ring/ inside api/)
- Webhook receiver, HMAC-SHA256 verification with the key from the console, event normaliser for motion, doorbell press, contact open/close, temperature/humidity, air quality, device online/offline.
- Night Watch rules: door open 23:00 to 06:00; no motion by 10:00; hall temperature under 18 C for 2 hours; air quality alert; device offline 24 h. Each rule emits a calm signal, never an alarm.
- Sandbox: Ring Developer Console Playground for tokens and live-view simulation; `scripts/ring_simulate.py` signs and posts synthetic events for the demo and tests.
- Account linking redirect URI set once the API URL exists.

### 2.6 Alexa+ (mcp/ + alexa-sim/)
- MCP server mounted at `/mcp`: Streamable HTTP, protocol version 2025-11-25, tools `get_today_board`, `confirm_medication`, `start_heart_session`, `get_family_status`, `request_refill` (returns a checkout intent; no real payment), resource `vita-heart://board/{household}` as an MCP Apps-style HTML card. Round trip under 500 ms (DynamoDB only, no model call on the hot path). OAuth 2.1 with PKCE, 401 without WWW-Authenticate on anonymous calls (the toolkit's stated requirement).
- Simulated Alexa+ surface at `/alexa-sim`: a web page styled as a conversation view; microphone via the browser's Web Speech API (real voice), utterance to Bedrock for tool selection, MCP call over Streamable HTTP, MCP App card rendered. The TV reacts live. Repo includes the simulation source, as the rules require.
- Real onboarding attempt with `alexa-ai` recorded in the friction log (toolkit is partner-only today).

### 2.7 Open source (mini challenge)
- Candidate A: publish `@gravitilabs/react-native-vega-sse`, a tiny SSE client that works on Vega's runtime, with tests and a Vega example. Candidate B: a PR to an AmazonAppDev sample adding a live-data pattern. Decision at Phase 6 start based on what the runtime actually lacked.

---

## 3. Phases, tasks, acceptance

Dates are Istanbul. Each phase ends with a commit tagged `phase-N`, a green test run, and a screenshot or recording in `docs/proof/`. VitaCabinet (AWS hackathon) still needs its video and final submit by 14 Sep; that is the founder's task and is blocked out on the calendar below.

### Phase 0. Access and tooling (5 Sep). DONE
Repo, Vega SDK, Virtual Device, hello world running, Builder Tools MCP, Ring app + credentials, Devpost draft, AWS CLI + Python env, Bee CLI. Remaining founder items: AWS credits form submit, (optional) Bee login.

### Phase 1. Foundation (5 to 8 Sep)
1.1 This plan committed; architecture diagram generated by script (`scripts/make_diagram.py`, PNG in docs/).
1.2 Repo layout: `tv/ api/ agents/ mcp/ alexa-sim/ watch/ scripts/ docs/ tests/`, root README with run instructions, `.github/workflows/ci.yml` (pytest + jest + lint).
1.3 API skeleton: FastAPI app, DynamoDB table `vitaheart`, seed script for household `AHMET1`, endpoints `/health`, `/board`, `/events` (long-poll), `/family/messages`, `/checkin`. Deployed via `scripts/deploy.py` (idempotent: IAM role, Lambda, API GW, DynamoDB). Public URL recorded in docs/URLS.md.
1.4 TV: design tokens, rail navigation, `MorningBoard` bound to the live API, long-poll client, `Pairing` screen (household code entry with D-pad).
1.5 Proof: change a family message in DynamoDB; it appears on the Virtual Device within 2 s. Recording in docs/proof/phase1.mov (OBS).
Acceptance: `pytest` and `jest` green; app on VVD shows cloud data; CI green on GitHub.

### Phase 2. Medications (9 to 13 Sep)
2.1 Vendor VitaCabinet tools with attribution (`agents/vendored/`), tests against live RxNorm and openFDA.
2.2 Photo intake: web page `/cabinet` (phone camera capture, uploads to S3 via presigned URL). Nova Lite Reader returns name + strength per box; Identifier confirms via RxNorm; Watchman checks recalls; schedule builder turns "twice daily" into household times (the VitaCircle rule: never silently pick 9 am; ask once on the TV).
2.3 AgentCore Runtime deployed (`agents/agentcore_entry.py`), trace written to DynamoDB, visible on `/trace/<job>` and on the TV Family screen.
2.4 TV `MedicationMoment`: due doses, box photos, OK to confirm, recall shown as a pharmacist question. Doses land in `DOSE#`.
Acceptance: photograph three real boxes from the founder's kitchen; all three identified or honestly marked unreadable; one seeded recalled lot shows the question; confirm from the remote updates DynamoDB.

### Phase 3. Heart Session (14 to 19 Sep)
3.1 Session engine (`tv/src/session/engine.ts`, pure TypeScript, fully unit-tested): seated protocol 10 min (warm 2, work 3, rest 1, work 3, cool 1), zones from age (Tanaka 208 minus 0.7 x age), adaptation rules (extend rest when HR above zone for 20 s; shorten set when recovery under 10 bpm per minute), ending rules.
3.2 Watch app `VitaHeartWatch` streaming HR to `/session/hr`; pairing by code; xcodegen project; on-device test on the founder's Watch (founder installs via Xcode once).
3.3 TV `HeartSession`: big number, 60 s trace, zone band, coach line, remote-only controls. the events channel carries HR at 1 Hz.
3.4 Replay tool from a real HealthKit export, labelled "recorded".
3.5 Coach agent on AgentCore writes the one sentence per interval and the session summary.
Acceptance: live HR from the Watch visible on the VVD within 3 s of the wrist; engine tests cover every rule; a full 10-minute session recorded to DynamoDB.

### Phase 4. Family and Night Watch (20 to 25 Sep)
4.1 Ring webhook receiver with HMAC verification and tests using the console key; `scripts/ring_simulate.py`; account linking redirect URI set in the console; Playground token flow documented.
4.2 Night Watch rules + agent; EventBridge 21:00 schedule; SNS email to Selin; `SUMMARY#` stored; TV `Family` screen shows summary, messages, and the agents' trace.
4.3 Family web page `/family/<code>` (mobile) to read the summary and reply; reply appears on TV via the events channel. (Integration with the real Vita iOS app is documented as the production path, not built here.)
4.4 "I'm up" check-in on the Morning Board; missed check-in by 10:00 becomes a Night Watch signal.
Acceptance: simulated door-at-03:10 and no-motion-by-10:00 produce the calm card on TV and the correct sentence in the 21:00 email; no rule ever uses the word alarm.

### Phase 5. Alexa+ (26 Sep to 3 Oct)
5.1 MCP server at `/mcp` (Python `mcp` SDK, Streamable HTTP, 2025-11-25), five tools + board resource, OAuth 2.1 PKCE demo client, latency test under 500 ms p95, MCP Inspector run recorded.
5.2 `/alexa-sim`: conversation UI, browser speech recognition, Bedrock tool selection, MCP call, MCP App card, TV reacts live.
5.3 `alexa-ai` onboarding attempt with the real CLI path; every step and refusal logged in FRICTION-LOG.md; support request sent for Preview access.
Acceptance: "tell Vita Heart I took the evening ones" spoken into the sim confirms the dose and the TV updates within 1 s; Inspector shows spec version and tools; p95 latency documented.

### Phase 6. Open source, hardening, audits (4 to 10 Oct)
6.1 Open-source contribution shipped (Candidate A or B), with tests, README, and the required Devpost fields (URL, repo, GitHub username, description).
6.2 Six-audit pass from the playbook: reliability (fallback chains), security (secrets, HMAC, CORS), honesty (every "recorded" label), fingerprints (no AI-styled copy), legibility (trace pages), performance (cold starts measured).
6.3 Product feedback per tool (Vega SDK, Builder Tools MCP, Ring API, Ring Playground, Bee CLI if used, Alexa AI CLI, AgentCore, Strands, Bedrock), feature requests with urgency, friction log to 12+ entries.
6.4 README, architecture PNG, docs/APPSTORE-LISTING.md, docs/TESTING.md (judge instructions with a demo household code).
Acceptance: fresh clone runs with the README alone (tested in a clean directory); CI green; audits written with fixes committed.

### Phase 7. Demo and submission assets (11 to 17 Oct)
7.1 Script per playbook 08 (Setup 20 s, Watch 100 s, Payoff 50 s), the three mandatory lines, pre-flight checklist, timing guard.
7.2 Recording: OBS scene with VVD window, phone camera for the Watch, browser for the Alexa+ sim, family page. One unedited take; 2:50 max. Public YouTube upload, English.
7.3 Devpost: description, built-with tags, try-it links, 6 gallery images (3:2), video link, tracks (Fire TV, Alexa+), minis (AWS Builder, Open Source), pre-existing disclosure text, product feedback, friction logs, feature requests, testing instructions with credentials.
Acceptance: a stranger reads the Devpost page and can run the demo household in under 5 minutes.

### Phase 8. Buffer and submit (18 to 22 Oct)
Fix what the dry run broke. Submit Thu 22 Oct before 20:00 Istanbul. Never the last day.

---

## 4. Non-functional rules (apply in every phase)
- No Google or Gemini code anywhere. Bedrock models only.
- No health claims. Words allowed: reminder, check-in, session, summary, question for the pharmacist. Words banned: monitor, diagnose, alarm, detect (for people).
- Nothing synthetic is shown as live. Recorded data is labelled on screen.
- Secrets never in the repo. `keys-ring.env` and AWS credentials stay outside `~/dev/vita-heart`.
- Every external call has a fallback and a one-sentence honest message on the TV.
- Commit small, push daily, tag phases. Co-author trailer on commits.
- The founder decides names and anything customer-facing before it is created in public.

## 5. Risks and mitigations
| Risk | Mitigation |
|---|---|
| Vega runtime fetch quirks | long-poll client with 2 s fallback; log as friction |
| API Gateway 30 s limit | 20 s long-poll cycles; alternative: AppSync Events if needed |
| Watch app cannot be installed in time | Replay tool from a real export, labelled |
| Ring sandbox lacks sensor events | Signed synthetic events via `ring_simulate.py`, disclosed |
| Bedrock model access in eu-north-1 | Nova Lite/Pro default; Claude optional; measured on day 1 of Phase 2 |
| Founder time collides with VitaCabinet 14 Sep | Phases 1 and 2 need only Claude; founder items listed per phase |
| Judges cannot run the TV app | Video shows the simulator; testing doc gives the web trace, family page and MCP Inspector steps |
