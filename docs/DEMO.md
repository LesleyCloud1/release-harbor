# Three-minute employer demo

**0:00 — Problem.** “A passing build does not prove a release can serve requests. I wanted a small platform that gates traffic on readiness and makes failure recovery visible.”

**0:20 — Deploy v1.** Show the event log and live endpoint. Explain that a real child process starts on its own port; the stable route points to it only after three probes.

**0:50 — Deploy v2.** Show the changed price in the live response. Explain candidate and active separation.

**1:15 — Break it.** Deploy v3-broken. Show the failure event and prove v2 still serves. The red failure is expected, not a fake UI state.

**1:55 — Roll back.** Start a rollback. Show its new history record and the v1 response. Explain why rollback must pass readiness too.

**2:20 — Evidence.** Show tests, CI, SQLite events, and the container publishing workflow. Distinguish local runtime from the optional Kubernetes manifest and ECR Terraform module.

**2:45 — Tradeoff.** “This is a single-controller prototype. My next step is an EasyShop Docker adapter, then reconciliation and identity before multi-user cloud deployment.”

Resume bullet after you have run and understood the project:

> Built a Python deployment control plane with health-gated traffic promotion, rollback, SQLite event history, and automated failure-isolation tests; added container packaging, GitHub Actions, and documented Kubernetes/AWS deployment patterns.

Do not claim production adoption, uptime improvements, or employer use without actual evidence.
