# Open Source mini challenge

**Contribution:** a new open-source project, `ring-webhook-kit` (MIT).
**URL:** https://github.com/bayraktartahsin/ring-webhook-kit
**Project repo:** https://github.com/bayraktartahsin/vita-heart · **GitHub username:** bayraktartahsin

**What it is.** A standard-library Python package that verifies Ring Partner API webhook signatures
(HMAC-SHA256 over the raw body, `X-Signature: sha256=<hex>`), normalises Ring's event names and
payload shapes into a small vocabulary, and ships `ring-webhook-sim`, a CLI that posts correctly
signed test events (single events or caretaking scenarios) to any endpoint.

**How it works.** `verify()` is a constant-time comparison against the recomputed digest;
`normalise()` maps known event types and keeps unknown ones as `ring.<name>` with the raw body;
the simulator builds payloads with `meta.request_id` and signs them with your key from an env var
or a local keys file. Three tests cover signing, normalisation and scenario uniqueness.

**Why it matters.** Every Ring-track participant has to write these three pieces before their first
real feature, and the public docs (September 2026) give the header name and the algorithm but no
code and no sensor payload examples. Vita Heart's own Ring pipeline was extracted into this package
after it had verified live deliveries and survived a real bug (idempotency kept in Lambda memory);
the README carries both lessons.
