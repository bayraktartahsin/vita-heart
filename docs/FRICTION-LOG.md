# Friction log

Format per the hackathon brief: task, steps, expected vs actual, severity, workaround, suggestion.
Severity: blocker / high / medium / low. Dates are 2026.

## 1. Alexa+ MCP Toolkit CLI is not installable without a partner AWS role (5 Sep)
- Task: install `@alexa-ai/cli` to build a real Alexa+ MCP add-on.
- Steps: followed "Set Up Your Development Environment". Step 1 requires assuming `arn:aws:iam::372468808636:role/AddOn3PDeveloperToolsRead` from "the AWS account that you provided to the Alexa Solutions Architect". `aws sts assume-role` returned AccessDenied. `npm install -g @alexa-ai/cli` returns 404 because the package lives in a private CodeArtifact repository behind that role.
- Expected: a public preview path for hackathon participants, or a clear "request access" link.
- Actual: no request path on the docs page; the home page says "available to select partners only".
- Severity: blocker for the real path. Workaround: the hackathon's simulated Alexa+ experience plus a real Streamable HTTP MCP server.
- Suggestion: publish the CLI to npm with a Login-with-Amazon gate, or add a request-access form to the docs home.

## 2. `react-native build-vega` fails on a project path containing a space (5 Sep)
- Task: first debug build of the generated helloWorld project under `~/Documents/New Apps/...`.
- Steps: `npm install && npm run build:debug`.
- Expected: a build, or a clear error about the path.
- Actual: `/bin/sh: /Users/bayraktar/Documents/New: is a directory` from `kepler-module-manifest-builder`, then "Unable to generate a manifest".
- Severity: high (misleading error, common macOS folder names have spaces). Workaround: move the project to `~/dev/vita-heart`.
- Suggestion: quote paths in the manifest builder's shell invocation; `vega project generate` could warn when the output path has spaces.

## 3. A React Native app's fetch() silently does nothing without `com.amazon.network.service` in the manifest (5 Sep)
- Task: call an HTTPS API from the generated helloWorld app.
- Steps: added fetch calls; built; launched on the Virtual Device; watched the API's Lambda logs.
- Expected: a request, or an error in the device log.
- Actual: no request and no error line in `vega device start-log-stream`. The generated template has no `[wants]` section; the fix is only discoverable by reading Amazon's video sample manifest.
- Verified by A/B: the same app built with the entry made 4 API calls in 45 s; built without it, 0 calls in 35 s, no error logged.
- Severity: high for newcomers. Workaround: add `[[wants.service]] id = "com.amazon.network.service"`.
- Suggestion: the helloWorld template should include the network service (commented out with one line of explanation), and the runtime should log a denied network call.

## 4. No screenshot or screen-recording command for the Vega Virtual Device (5 Sep)
- Task: capture proof of the app running for the submission.
- Steps: `vega device --help`, `vega virtual-device --help`; on-device `screenshooter -r /scratch/shot.png`; QEMU QMP `screendump`.
- Actual: no CLI command; `screenshooter` fails for app_user with "creating a buffer file for 8294400 B failed: Permission denied"; QMP screendump returns a black frame (GL-accelerated display).
- Severity: medium (every demo video needs it). Workaround: macOS window capture / OBS.
- Suggestion: `vega device screenshot <file.png>` and `vega virtual-device record`.

## 5. Non-interactive installer prints "SDK linking not available, skipping" with no explanation (5 Sep)
- Task: `NONINTERACTIVE=true bash get_vvm.sh`.
- Actual: the line above, then a successful SDK download. Unclear whether anything was skipped that matters.
- Severity: low. Suggestion: say what linking is and when it applies.

## 6. Ring app credentials are shown once with no rotation (5 Sep)
- Task: create a private Ring app and store its credentials.
- Actual: Client ID, Client Secret and HMAC key shown once; only "Download CSV" or copy; "contact support" to get new ones.
- Severity: low. Suggestion: a "rotate secret" button on the app page.

## 7. Ring Playground is the best onboarding tool and is not linked from Get Started (5 Sep)
- The Playground (token, Explore APIs, simulate live view) answers most first-hour questions. The public docs never mention it.
- Severity: low. Suggestion: make it the first link in Get Started.

## 8. Builder Tools `init-context --agent claude-code-cli` reports one installed skill (5 Sep)
- Actual: summary lists `vega-multi-tv-migration` only; unclear whether other skills exist for this agent or were skipped.
- Severity: low. Suggestion: list every skill considered and why each was or was not installed.

## 9. DynamoDB refuses Python floats; the error surfaces as a 500 two layers up (5 Sep)
- Task: store a Ring temperature reading (16.8) as a signal. Actual: `Float types are not supported. Use Decimal types instead` inside boto3, a 500 to Ring's webhook. Severity: medium for anyone new to DynamoDB. Workaround: a `storable()` conversion at the store boundary. Suggestion (AWS): let the resource layer accept floats with a documented precision, or make the error name the offending attribute.

## 10. Bedrock AgentCore starter toolkit is deprecated on install, docs still point to it (5 Sep)
- `pip install bedrock-agentcore-starter-toolkit` prints a deprecation notice pointing to the new `@aws/agentcore` CLI, while the Runtime docs and samples still show `agentcore configure/deploy`. Both work; a newcomer does not know which to trust. Severity: low. Suggestion: one dated migration note at the top of the Runtime quick start.

## 11. AgentCore direct code deploy: a `-rf` requirements path outside the project root is silently ignored (5 Sep)
- Task: `agentcore configure -rf agents/requirements.txt`. Actual: first runtime start failed with `No module named 'bedrock_agentcore'`; moving the file to `./requirements.txt` fixed it. Severity: high (a silent packaging miss becomes a runtime failure minutes later). Suggestion: fail at configure time if the requirements file will not be packaged, and print which file was used in the deploy summary.

## 12. Ring webhook payload schema is not in the public docs (5 Sep)
- The API reference names the `X-Signature` header and `sha256=<hex>` HMAC, and lists event type names, but no example body for sensor events (contact, temperature, air quality). Severity: medium (sensor use cases are a stated priority). Workaround: a tolerant normaliser. Suggestion: one JSON example per event type, and a "send test event" button in the Playground.

## 13. Alexa+ MCP contract vs the MCP SDK defaults (5 Sep)
- The Alexa+ docs require a bare 401 for anonymous calls; the Python MCP SDK's auth middleware returns 401 with `WWW-Authenticate` per RFC 9728, and its transport security guard returns 421 for any non-localhost Host. Neither is wrong; they disagree. Severity: medium. Suggestion (Alexa docs): state whether RFC 9728 headers are tolerated; (SDK): mention the host guard in the Streamable HTTP deployment notes.
