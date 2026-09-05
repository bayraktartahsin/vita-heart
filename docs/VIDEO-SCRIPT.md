# Video script (2:50, one unedited take, English, no music)

Method: Setup → Watch → Payoff. Judges are not required to watch past 3:00, so the wow moment
(live heart rate on the television) is at 1:05, not at the end. Every scene shows a real
surface: the Vega Virtual Device window (OBS scene 1), the phone (scene 2, camera on the iPhone),
the browser (scene 3). The three mandatory lines are marked ★.

## Pre-flight (10 min before)
- `python scripts/demo_setup.py` (clean state: two medicines, clock set, Ring night scenario, summary).
- Time: record between 07:30 and 08:20 Istanbul, or override the clock so the morning dose is due.
- VVD running with GUI, app launched, board visible. Family page open on the phone as Selin.
- Watch: Vita Heart app open on the wrist, household AHMET1, Developer Mode on.
- /alexa-sim open in Chrome, connected (PKCE done), microphone permission granted.
- OBS: 1920x1080, scenes 1/2/3, hotkeys F1/F2/F3, audio from the built-in mic. One take; if a scene breaks, restart from 0:00.

## 0:00 Setup (20 s) · scene 1, the television
★ "This is Vita Heart, a Fire TV app on Vega OS. It turns the television an older parent already watches into their health room. Ahmet is 72 and lives alone in Istanbul; his daughter Selin lives in Ankara. Everything you will see is live: the board, the agents, the Watch, the door."

## 0:20 Watch (100 s)
**0:20 Morning Board (scene 1).** "Günaydın Ahmet. One tablet due, one line from Selin, one button." Press OK on *I'm up*. Cut to scene 2: the tick appears on Selin's phone. "That took under a second, through one events channel every surface shares."

**0:35 Medication Moment (scene 1).** *Show me*. "These boxes were photographed once by Selin. Nova Lite read the print, RxNorm confirmed CORASPIN is aspirin, openFDA found live recalls against specific batches. The television does not say 'recalled'. It gives him the question for the pharmacist." Press *I took it*.

**0:55 Alexa+ (scene 3).** Speak: "How is Dad doing today?" The reply comes from the MCP server through OAuth 2.1 PKCE. Speak: "Tell Vita Heart he took the morning Coraspin." Cut to scene 1: the dose flips to taken. ★ "Voice, remote and screen in one flow. The MCP server runs on spec 2025-11-25 over Streamable HTTP; anonymous calls get a bare 401, as the Alexa+ toolkit requires."

**1:05 Heart Session (scene 1, then a phone camera on the wrist for 5 s).** *Start with my Watch*. Start on the Watch. "His real heart rate, from his own Watch, on his television." Wait for two or three samples. "The coach adapts: twenty seconds above the ceiling ends the set early and extends the rest. Nothing here is synthetic; when a replay is used, the screen says so."

**1:40 The door (scene 3, terminal).** Run `python scripts/ring_simulate.py night`. "Ring sensors at the door and in the hall. These events are signed exactly as Ring signs them; they are simulated because there is no Ring device in this flat, and the summary says so."

**1:50 Family (scene 1 → scene 2).** *Family* on the TV; then the phone. Run Night Watch (`/night/run`). Read the paragraph aloud as it appears: "Selin, this morning at 03:10 the front door opened, the hall has been under 18 degrees since 06:00…" "Strands agents on Bedrock AgentCore wrote that from facts only; the Scribe holds no tools, by design. She gets it by email at nine."

## 2:00 Payoff (50 s) · scene 1 with the architecture diagram picture-in-picture
★ "Why the television: adults over 65 watch more television than any other age group, and their children live elsewhere. Vita Heart is Vega OS native, multi-modal, adapts to the household, and connects the living room, the front door and the cloud on AWS: Lambda, DynamoDB, EventBridge, SNS, and Strands agents on AgentCore. It is backed by Vita, our shipping iOS health app. Repo, tests, friction log and testing instructions are in the submission. Thank you."

## Timing guard
Total 2:50 at speaking pace 150 wpm. If the Watch does not connect within 15 s at 1:05, say "the Watch is out of range; here is a recorded session, labelled as such" and start the replay. Never wait silently.
