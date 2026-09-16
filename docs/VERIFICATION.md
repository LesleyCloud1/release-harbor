# Verification record

## Observed locally — September 15, 2026

- Python 3.12: all 13 automated tests passed. These launch real workload processes and make real HTTP requests.
- Python compile check and JavaScript syntax check passed.
- Browser: v1 deployment, v2 deployment, broken-release failure, and rollback to v1 succeeded. History showed three successful operations and one expected failure.
- Desktop dashboard inspected visually; screenshot captured from the running application.

## Infrastructure

Docker, Kubernetes, and Terraform were not installed on the local test machine. Container smoke testing and Terraform validation are configured in GitHub Actions; remote results will be recorded after publication. No AWS resources were created and no Kubernetes cluster was provisioned.
