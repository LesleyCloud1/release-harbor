# Verification record

## Observed locally — September 15, 2026

- Python 3.12: all 13 automated tests passed. These launch real workload processes and make real HTTP requests.
- Python compile check and JavaScript syntax check passed.
- Browser: v1 deployment, v2 deployment, broken-release failure, and rollback to v1 succeeded. History showed three successful operations and one expected failure.
- Desktop dashboard inspected visually; screenshot captured from the running application.

## Observed in GitHub Actions

[Verification run](https://github.com/LesleyCloud1/release-harbor/actions/runs/35060859073) passed:

- All 13 tests on each of Python 3.11, 3.12, and 3.13.
- Docker image build and live container smoke test: v1 promotion, broken candidate rejection, and v1 continuity.
- Terraform format, initialization, and configuration validation.

## Not executed

No AWS resources were created. No Kubernetes cluster deployment was attempted. The manual GHCR publish workflow was not run; it is opt-in. Terraform validation checks configuration, not whether a real AWS deployment will succeed with a particular account's permissions and policies.
