# Understand Release Harbor

## The idea

Think of a theater changing sets. The next set is built behind the curtain. You inspect it before revealing it. If something is broken, the audience keeps seeing the working set. Release Harbor does that with programs.

A **deployment** means starting a chosen version of software and making it available. A **control plane** is the program that decides what should run. A **workload** is the program doing the actual work. Here, the controller and catalog workload are separate operating-system processes.

## Follow one click

1. In `harbor/static/app.js`, the Deploy button calls `act()`. It sends a JSON version and an authorization header to `/api/deploy`.
2. `harbor/server.py` checks the request's host, origin, operator key, and body. An unauthorized request never reaches the engine.
3. `Engine.deploy()` in `harbor/engine.py` checks the fixed release catalog and reserves the deployment slot while holding a lock. It writes a queued record before starting a worker thread.
4. `_run()` starts `sample.py` using a list of subprocess arguments. No shell interprets the release name. The child asks the operating system for an unused port and prints it to its parent.
5. The engine calls the child's HTTP health endpoint. Three consecutive responses must say the expected version is healthy.
6. On success, the engine changes `active` under a lock. The stable `/demo` route now reads from that process. It then terminates the previous process.
7. On failure, the candidate is terminated in `finally`. The old active pointer is never replaced.
8. The browser polls `/api/state` to show history and events. `textContent` renders server data as text, not executable HTML.

## Why a thread?

Startup and health checks take time. If the request waited for everything, a user would be stuck waiting on an HTTP connection. The API returns **202 Accepted**, meaning “the operation has started.” A worker handles the slow part; the browser checks progress separately.

## Why a lock?

Imagine two people deploying at once. Without coordination, each could replace the other's active process. A reentrant lock protects shared state, and the busy flag allows one deployment at a time. A second request gets **409 Conflict**. This coordinates threads in one controller; it does not coordinate two separate controller processes.

## What SQLite does

SQLite is a database stored in a local file. One table stores deployments; another stores events. Parameterized SQL separates values from SQL instructions. Records survive restarting the controller. Process objects do not, so restart recovery marks unfinished records interrupted and starts without an active workload.

## What rollback really means

Rollback selects the most recent successful version different from the active version. It creates a new deployment and runs the same readiness checks. It does not simply claim that an old release is active. This demo's versions use one source file plus different configuration; production releases would use immutable stored artifacts.

## The operator key

The terminal prints a random key. The user pastes it into a password field. JavaScript retains it only in that input's memory and sends it as a bearer token for writes. The server uses a constant-time comparison. The key is not a user account or an enterprise identity system. Read endpoints are unauthenticated because this edition is intended for loopback use.

## Why infrastructure files exist separately

The Dockerfile packages the controller and sample. The Kubernetes manifest demonstrates running the sample as a normal cluster workload. Terraform demonstrates an AWS registry. Neither silently turns the local controller into an EKS deployment service. Connecting those components requires an adapter, identity, network access, and a reconciliation design.

## Explain it in an interview

“I built a small deployment control plane. It starts a candidate, checks readiness, and only then switches a stable route. I tested a deliberately unhealthy release to prove the old version keeps serving. I used SQLite for deployment evidence and made rollback go through the same verification path. I also documented the limits: one controller, local process runtime, and no continuous health monitoring yet.”

## Exercises

- Add a v4 catalog release, then test that it can be deployed and rolled back.
- Add a measured startup duration to each record and show it in the dashboard.
- Decide how an EasyShop adapter should prove that both the application and MySQL are ready.
- Explain what happens if the controller is killed after traffic switches but before a database commit. That leads to the next major topic: reconciliation.
