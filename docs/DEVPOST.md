# Devpost fields (paste-ready)

**Project name:** Vita Heart
**Elevator pitch (200):** The television an older parent already watches becomes their health room: meds from a photo, live Watch heart rate on the TV, voice + remote in one flow, one calm summary to the family.
**Tracks:** Fire TV (primary), Alexa+. **Mini challenges:** AWS Builder, Open Source.
**Built with:** vega-os, react-native, typescript, python, fastapi, aws-lambda, api-gateway, dynamodb, s3, sns, eventbridge, amazon-bedrock, amazon-nova, claude, strands-agents, bedrock-agentcore, mcp, oauth2, ring-api, healthkit, watchos, swiftui, rxnorm, openfda
**Try it out:** repo · live API /board?household=AHMET1 · /family?household=AHMET1 · /cabinet?household=AHMET1 · /alexa-sim · video

## About the project (Markdown)

### Inspiration
Every health app talks to the person holding the phone. The person who most needs help, a 72-year-old living alone, does not hold a phone all day. He watches television. Vita Heart puts the health room on the screen he already looks at, and puts his daughter, Alexa+, the front door and a fleet of agents around it.

### What it does
- **Morning Board** on Fire TV (Vega OS): greeting, what is due, one line from the family, one big button, *I'm up*. The family's phone shows the tick in under a second.
- **Medication Moment**: boxes photographed once from a phone. Amazon Nova Lite reads the print and must quote its own transcript (a blank photo cannot become a made-up drug); RxNorm confirms identity through a Turkish-brand bridge; openFDA supplies live recalls with lot numbers. The TV never says "recalled": it gives the question to ask the pharmacist. "Twice daily" becomes *slots*; the household maps slots to its own clock on the TV, once.
- **Heart Session**: ten seated minutes. A standalone watchOS app streams his heart rate to the television; the coach ends a set early after twenty seconds above the ceiling and shortens the next one after slow recovery. The number on screen always carries its source: live, recorded, or test signal.
- **Alexa+**: a real MCP server (spec 2025-11-25, Streamable HTTP, OAuth 2.1 PKCE, bare 401 for anonymous calls) with five tools and a board card; tool calls take 120 to 160 ms behind API Gateway. The simulated Alexa+ surface uses the browser's speech recognition and Claude on Bedrock to choose a tool from the server's own schemas. "Tell Vita Heart I took the morning Coraspin" flips the dose on the TV within a second.
- **Ring**: signed webhooks (HMAC-SHA256, durable idempotency), sensors normalised; Night Watch rules for the door at night, a quiet morning, a cold hall.
- **Night Watch**: at 21:00 Strands agents on Bedrock AgentCore turn the day's facts into one calm paragraph for the family, delivered by SNS. The words alarm, monitor, detect and diagnose never appear.

### How we built it
React Native 0.83 on Vega OS (TVFocusGuideView, D-pad only, 32 px minimum type). FastAPI on Lambda behind API Gateway with one idempotent deploy script; DynamoDB single table; S3 for photos; a long-poll events channel every surface reads. Strands Agents on Bedrock AgentCore Runtime (Identifier, Watchman, Scribe, Coach), every tool call traced. The MCP server runs inside the API. Tests: 37 pytest (moto) + 15 jest, plus live tests behind a flag.

### Challenges
The Alexa+ toolkit is partner-only, so the surface is the sanctioned simulation over a real server. Lambda cannot stream through API Gateway, so live updates are a long-poll. Nova Lite completed a blank image into a plausible medicine until it was grounded in its own transcript. The MCP SDK's session manager runs once per instance and its host guard rejects any non-localhost Host; both are documented in the friction log and one became an open-source contribution.

### What we learned
Reading is not identifying. Slots are not times. A Scribe with tools becomes a doctor; ours has none. And a television is a health device the customer already owns.

### What's next
Ship to the Fire TV Appstore with the Vita account as the family side; connect a Ring household; real Alexa+ certification when the toolkit opens.

## If your project existed before the hackathon
Vita is our shipping iOS health companion (App Store, 2026). Everything in this repository was created during the submission window: the Vega OS TV app, the API, the Strands fleet on AgentCore, the Ring pipeline, the MCP server and the simulated Alexa+ surface, the Watch app. Two things are reused with attribution: medicine-identification tools from our open-source VitaCabinet (RxNorm and openFDA lookups, Apache-2.0, vendored under agents/vendored with a NOTICE), and read-only access to a Vita household through a scoped code. The iOS app itself is not part of this submission.

## Product feedback
See docs/PRODUCT-FEEDBACK.md (paste in full).

## Friction log
See docs/FRICTION-LOG.md (13 entries; paste in full).

## Feature requests
1. Vega: `vega device screenshot` and `vega virtual-device record` (critical for every demo video).
2. Vega helloWorld template: include the network service entry, commented, with one line of explanation (important).
3. Alexa+: a public preview path for the MCP Toolkit gated by Login with Amazon (important).
4. Ring: one JSON example per event type and a "send test event" button in the Playground (important).
5. AgentCore: fail at configure time when a requirements file will not be packaged (important).
6. Bedrock: a self-serve request for models that appear in the list but are not enabled for the account (nice-to-have).

## Open Source mini challenge fields
Contribution URL: (PR link) · Repository: github.com/bayraktartahsin/vita-heart · GitHub username: bayraktartahsin · Description: see docs/OPEN-SOURCE.md.

## AWS Builder mini challenge
Amazon Bedrock (Nova Lite for label reading, Claude Sonnet 4.5 for prose), Bedrock AgentCore Runtime hosting Strands agents with observability, Lambda + API Gateway, DynamoDB, S3, SNS, EventBridge. Documented in README and docs/architecture.png.

## Testing instructions
See docs/TESTING.md (paste in full; demo household AHMET1, no credentials needed).
