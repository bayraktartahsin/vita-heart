# Product feedback (what we used, what worked, what needs work, would we build with it again)

**Vega OS SDK 0.24 + Vega CLI 1.3.4.** Used for the TV app end to end. Worked: `vega project generate`, the Virtual Device (boots in ~40 s, stable for hours), `run-app`, the Builder Tools MCP docs search from Claude Code. Needs work: paths with spaces break the manifest builder; the helloWorld template has no `[wants]` network entry so fetch silently does nothing; no screenshot/recording command; JS console output is not in `start-log-stream`. Onboarding: two hours from zero to an app on the Virtual Device, most of it spent on the two silent failures above. Again: yes; Vega is a pleasant React Native target once the manifest is right.

**Amazon Bedrock (Nova Lite, Nova Pro, Claude Sonnet 4.5) via Converse.** Worked: one API for vision and text; Nova Lite reads a label in about a second. Needs work: Nova Lite completes blank images into plausible medicines (we ground it in its own transcript); Claude Sonnet 5 shows in the model list but is not enabled for the account with no self-serve path. Again: yes.

**Strands Agents SDK 1.54.** Worked: hooks for tool tracing, `structured_output`, model-agnostic. Needs work: nothing blocking. Again: yes.

**Bedrock AgentCore Runtime (direct code deploy).** Worked: no Docker, ~4 minutes to a running fleet, observability on. Needs work: deprecated toolkit notice vs docs; requirements path silently ignored (friction 10, 11); first cold start exceeded 30 s once. Again: yes.

**Ring Developer Console, Partner API, Playground.** Worked: access was immediate, scopes are clear, the Playground token flow is the fastest onboarding of all four tracks. Needs work: no sensor payload examples; credentials shown once; account linking form needs URLs before a private app can be tested against a real account. Again: yes, and we would ship the caretaking sensors app.

**Alexa+ MCP Toolkit / alexa-ai CLI.** Could not use: partner-only distribution through a private CodeArtifact role. Built the sanctioned simulation plus a real MCP server instead. Needs work: a public preview path with Login with Amazon. Would build with it again: as soon as it is reachable.

**Bee CLI 0.7.3.** Installed, not exercised (needs the iOS app). No opinion yet.

**AWS Lambda + API Gateway HTTP API + DynamoDB + S3 + SNS + EventBridge.** Worked as expected; the whole cloud side deploys from one idempotent script. Needs work: Function URLs 403 in this account regardless of policy (undiagnosed), no response streaming through the HTTP API.

**Amazon Devices Builder Tools MCP + skills.** Worked: documentation search from the editor. Needs work: the init summary lists one skill.
