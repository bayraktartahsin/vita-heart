# Decisions (with reasons)

| Date | Decision | Why |
|---|---|---|
| 5 Sep | Name: Vita Heart (not Hearth) | Founder's call; a name that needs explaining is a bad name. |
| 5 Sep | Long-poll `/events` instead of SSE | Lambda behind API Gateway buffers responses; Function URLs 403 in this account. Sub-second delivery, honest. |
| 5 Sep | Nova Lite reads labels, Claude Sonnet 4.5 writes prose, Nova Pro fallback | Measured in eu-north-1: 0.8 s vs 2.0 s for one word; Claude Sonnet 5 not enabled on the account. |
| 5 Sep | Reader must quote its own transcript | Nova Lite produced "Ibuprofen 200 mg" from a white rectangle. Grounding removed the failure class. |
| 5 Sep | Slots, not times, from labels | "Twice daily" is not 09:00. The household maps slots on the TV once. |
| 5 Sep | Fleet on AgentCore Runtime, direct code deploy | No Docker on the machine; the API Lambda stays small (3 MB) and calls the runtime. |
| 5 Sep | Scribe holds no tools; prompt forbids inference | It paraphrased "no seated session" into "not in his usual spot". Facts only now. |
| 5 Sep | Ring idempotency in DynamoDB, not memory | Lambda restarts made the same request_id count twice. |
| 5 Sep | MCP: per-event-loop server factory; host guard off | SDK's session manager runs once per instance; its localhost-only host check returned 421 behind API Gateway. Bearer auth guards the endpoint. |
| 5 Sep | Simulated Alexa+ surface, real MCP server | The MCP Toolkit is partner-only; the rules sanction the simulated path; the tools the model sees are the server's own. |
| 5 Sep | No Fire TV hardware | Not orderable to Istanbul; the rules accept the Vega simulator in the video. |
