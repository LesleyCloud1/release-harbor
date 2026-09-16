# Design decisions

| Decision | Benefit | Tradeoff |
|---|---|---|
| Python standard library | Reproducible demo with no package installation | HTTP server is unsuitable as a public production edge |
| Fixed workload catalog | No arbitrary command execution or URL fetch API | Adding applications requires code/adapters |
| Separate candidate process | Readiness can fail without replacing the active process | Uses extra capacity during transition |
| Three consecutive probes | A single transient success cannot promote a candidate | Still not sustained availability monitoring |
| Single deployment slot | Simple ordering and predictable rollback | No parallel services or distributed workers |
| SQLite + timestamped events | Durable, queryable evidence | Not tamper-proof and no multi-controller lease |
| Proxy lock during upstream read | Previous process is not retired while that read is underway | Slow request briefly delays promotion |
| Fresh process on rollback | Re-validates the rollback target | Needs historical artifacts for true production reproducibility |
| Local-only binding | Demo is easy to run without cloud credentials | Public access needs TLS, identity, policy, and a production server |

The database and runtime are not one atomic transaction. A crash can occur between runtime and database updates. Restart intentionally reports no active process; it does not infer health from old records. A production controller needs reconciliation, process/container ownership labels, leases, and idempotent operations.

Graceful shutdown cleans up owned child processes. An uncatchable kill can leave a child behind; this prototype does not adopt or reap orphan processes after restart. Do not run multiple controllers against one database.

## Reference material

- [GitHub: publishing container images](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)
- [Docker: SBOM and provenance in GitHub Actions](https://docs.docker.com/build/ci/github-actions/attestations/)
- [Kubernetes: Deployment lifecycle and progress deadlines](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

A Kubernetes progress deadline reports a stalled rollout; it does not itself perform an automatic rollback. The local engine's failed-candidate behavior is implemented here explicitly.
