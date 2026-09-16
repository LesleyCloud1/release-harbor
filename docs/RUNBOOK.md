# Operations runbook

## Local failed release

1. Inspect the newest failed deployment and activity log.
2. Open `/demo`; verify it still reports the previous healthy version.
3. Check that the failure reason is readiness timeout. The broken catalog deliberately returns HTTP 503.
4. Select a known healthy release. Never relabel a failed deployment as successful.

## Local rollback

1. Confirm there are at least two different successful versions in history.
2. Click Roll back. Observe a new operation of kind `rollback`.
3. Wait for `succeeded`, then inspect `/demo` and confirm the expected version.
4. Preserve the operation ID and event timestamps as evidence.

## Controller restart

Stop with Ctrl+C. History persists, active workloads are stopped. Start the controller again, copy its new key, and deploy a healthy version. An ungraceful process kill may leave orphan child processes; this prototype requires manual inspection in that case. Do not blindly kill unrelated Python processes.

## Optional Kubernetes workload

Prerequisites: an existing authorized cluster, kubectl, and a published image accessible to that cluster. Replace `IMAGE_PLACEHOLDER` with a digest-pinned image in a copy of `deploy/kubernetes/catalog.yaml`.

```bash
kubectl apply -f deploy/kubernetes/catalog.yaml
kubectl rollout status deployment/harbor-catalog --timeout=90s
kubectl get pods -l app=harbor-catalog
kubectl port-forward service/harbor-catalog 8000:80
```

This deploys the sample workload independently of the dashboard. On a stalled rollout, inspect `kubectl describe deployment harbor-catalog`, pod events, and logs. After confirming the previous revision is appropriate, use `kubectl rollout undo deployment/harbor-catalog` and verify rollout status again. Kubernetes reports progress deadline failures; automatic rollback is not built into this manifest.

## Optional AWS registry

Use an AWS profile with appropriate ECR permissions. Run `terraform init`, `terraform plan`, review the plan, then `terraform apply` from `infra/registry` only when you want real AWS resources. No credentials belong in source control. The ECR resource has force deletion disabled. Cleanup requires deliberate image and resource management; do not destroy a shared registry.
