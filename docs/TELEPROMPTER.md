# Vita Heart demo: teleprompter and run sheet

One take, 2:50, English, no music. You speak the **bold** lines exactly as written; you press the keys in `[brackets]`; Claude prepares everything before and does nothing during the take. If something breaks, use the recovery line for that scene and keep going. Never stop the recording.

Scenes in OBS: **1 TV** (the Vega Virtual Device window), **2 PHONE** (iPhone camera via Continuity Camera, or hold the phone up to the webcam), **3 BROWSER** (Chrome, /alexa-sim), **4 TERMINAL**. Hotkeys F1 F2 F3 F4. The whole take is recorded at 1920x1080 with the built-in microphone.

Keys on the Vega Virtual Device window: arrows = D-pad, Return = OK, Escape = Back.

---

## Before the take (Claude, 10 minutes before)
- `python scripts/demo_setup.py --due-now` (clean state; the morning dose is due now).
- `python scripts/preflight.py` must print READY.
- TV app relaunched on the Virtual Device, Morning Board visible, focus on *I'm up*.
- Chrome: `/alexa-sim` open and already connected (PKCE done), microphone allowed. Zoom 125%.
- Phone: `/family?household=AHMET1` open in Safari as Selin; screen brightness up.
- Watch: Vita Heart app open, household AHMET1, wrist warm (walk for two minutes first so the heart rate is above resting).
- Terminal: `cd ~/dev/vita-heart` with the ring command typed and not yet run.
- OBS: scenes checked one by one, audio meter moving when you speak, disk space checked. Record hotkey known.

## You, 60 seconds before
- Water. Sit. Read the first line silently once. Start the recording. Count two seconds of silence. Begin.

---

## 0:00  SETUP  (scene 1 TV, board on screen)

**This is Vita Heart, a Fire TV app on Vega OS. It turns the television an older parent already watches into their health room. Ahmet is seventy-two and lives alone in Istanbul. His daughter Selin lives in Ankara. Everything you are about to see is live: the television, the agents, the Watch, and the front door.**

(pace: calm, 20 seconds)

## 0:20  MORNING BOARD  (scene 1)

**Günaydın Ahmet. One tablet due. One line from Selin. One button.**

`[Return]` on *I'm up*.

`[F2]` scene 2 PHONE. Point at the family page; the "Said I'm up" tick has appeared.

**Selin's phone knows in under a second, through one events channel that every screen in this system shares.**

`[F1]` back to the TV.

Recovery: if the tick is slow, keep talking; it arrives within two seconds. Do not press again.

## 0:35  MEDICATION MOMENT  (scene 1)

`[↓]` to *Show me*, `[Return]`.

**These boxes were photographed once, by Selin, from her phone. Amazon Nova Lite read the print. RxNorm confirmed what it is. openFDA found live recalls, against specific batches.**

Point with the cursor at the safety line on the card.

**The television does not say "recalled". It gives him the question to ask the pharmacist.**

`[Return]` on *I took it*.

**Taken. That is now a fact the family and Alexa+ can both see.**

Recovery: if no dose shows as due, say **the dose window is later today; here is the list from this morning** and continue. Claude's due-now setup makes this unlikely.

## 0:55  ALEXA+  (scene 3 BROWSER)

`[F3]`. Click the microphone. Say clearly:

**How is Dad doing today?**

Wait for the spoken reply (about four seconds). Then click the microphone again:

**Tell Vita Heart he took the evening Glifor already.**

`[F1]` back to the TV. The evening dose flips to taken.

**Voice, the remote, and the screen, in one flow. That was a real MCP server on the 2025 spec over Streamable HTTP, with OAuth 2.1 PKCE. Anonymous calls get a bare 401, exactly as the Alexa+ toolkit requires. The toolkit itself is partner-only today, so this surface is the sanctioned simulation; the server behind it is the real one.**

Recovery: if the microphone does not pick up, type the same sentence in the box and press Enter. Say nothing about it.

## 1:15  HEART SESSION  (scene 1, then phone camera on the wrist)

`[Escape]` to the board if needed, `[→]` to *Start with my Watch*, `[Return]`.

On the Watch: tap **Start**. Wait for the first number on the television.

`[F2]` for five seconds: the Watch on your wrist showing the same number. `[F1]`.

**That is his real heart rate, from his own Watch, on his own television. Ten minutes, seated. The coach adapts: twenty seconds above the ceiling ends the set early and extends the rest; slow recovery shortens the next set. When a recording is used instead of a wrist, the screen says so. Nothing here is synthetic.**

Let it run for fifteen seconds so the trace draws. `[Return]` on *Stop*.

Recovery: if no number arrives within fifteen seconds, say **the Watch is out of range, so here is a recorded session, labelled as such**, press *Stop*, and Claude starts the replay from the terminal while you continue. The label on screen will read "recorded session".

## 1:45  THE FRONT DOOR  (scene 4 TERMINAL)

`[F4]`. Press `[Return]` on the prepared command. Signed events post one by one.

**Ring sensors at the door and in the hall. These events are signed exactly as Ring signs them. They are simulated, because there is no Ring device in this flat, and the summary will say so.**

## 1:55  FAMILY AND NIGHT WATCH  (scene 1, then 2)

`[F1]`. `[↓]` to *Family*, `[Return]`. The trace of what the agents looked up is on screen.

**Every tool call the agents made is on the screen, in his living room. Nothing is said about him behind his back.**

`[F2]`. On the phone, the family page shows tonight's paragraph (Claude ran Night Watch during the door scene). Read it aloud from the phone:

**"Selin, this morning at 03:10 the front door opened, the hall has been under 18 degrees since 06:00, he took both tablets, and did his seated session."**

**Strands agents on Bedrock AgentCore wrote that from facts only. The Scribe holds no tools, by design. She gets it by email at nine.**

## 2:15  PAYOFF  (scene 1, with the architecture picture in the corner)

`[F1]`.

**Why the television. Adults over sixty-five watch more television than any other age group, and their children live somewhere else. Vita Heart is native on Vega OS, multi-modal, it adapts to the household, and it connects the living room, the front door and the cloud: Lambda, DynamoDB, EventBridge, SNS, and Strands agents on AgentCore. It is backed by Vita, our shipping iOS health app. The repository has thirty-seven tests, a thirteen-entry friction log, an open-source package for Ring webhooks, and testing instructions with a live household for the judges. Thank you.**

Stop the recording after two seconds of silence.

---

## Timing marks (say these lines when the clock shows)
0:00 Setup · 0:20 Board · 0:35 Medication · 0:55 Alexa+ · 1:15 Heart · 1:45 Door · 1:55 Family · 2:15 Payoff · 2:50 end.
If you are more than 10 seconds late at 1:45, skip the Family screen on the TV and go straight to the phone.

## The three lines that must be in the video (they are)
1. What it is and who it is for (0:00). 2. What is real and what is simulated (0:55, 1:15, 1:45). 3. Why it wins the track: Vega native, multi-modal, household-adaptive, living room + door + cloud (2:15).

## Upload
YouTube, Public, title "Vita Heart: the health room on a Fire TV (Vega OS, Alexa+, Ring, AWS)", no music, no third-party logos. Paste the URL into the Devpost video field; that completes step 4 of 5.
