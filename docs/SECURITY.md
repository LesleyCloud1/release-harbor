# Security boundaries

This is a local, single-operator portfolio control plane. It is not hardened for Internet exposure.

- The default listener is `127.0.0.1`. Docker Compose also publishes only on loopback.
- Mutations require a random session key or a user-supplied `HARBOR_TOKEN` of at least 16 characters. Avoid placing real tokens in shell history.
- The dashboard stores no key in localStorage, cookies, URLs, or SQLite. Reloading clears its input.
- Requests with unrecognized hosts or foreign origins cannot mutate state.
- Read endpoints are unauthenticated and can contain deployment metadata. Do not place sensitive data in this edition.
- Fixed asset routes prevent arbitrary filesystem reads. Fixed release names prevent arbitrary command selection.
- Child processes use argument arrays with no shell. They are **not a security sandbox** and run as the controller's user.
- The CSP restricts scripts and assets to the same origin, and event text uses DOM textContent.
- SQLite history is operator-editable, not cryptographically protected audit evidence.
- `.env`, runtime databases, Terraform state, and variable files are ignored. No cloud credentials are needed for the demo.
- The sample has no persistent business data; rollback does not solve database schema migrations.

Before public deployment: replace the development HTTP server, add TLS and OIDC/RBAC, authenticate reads, add rate/body/read-time limits, isolate workloads, pin/verify artifacts, persist immutable audit records, and implement runtime reconciliation. The HTTP server is intentionally not defended against hostile slow connections.
