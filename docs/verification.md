# Verification

## Automated checks — gateway 0.1.2

Verified on 14 October 2026 with Python 3.12:

- Seven gateway tests passed, covering successful inference responses, upstream
  failures, malformed responses, validation, health checks, request IDs,
  metrics, and malformed Host headers.
- Python syntax compilation and `pip check` passed.
- GitHub Actions passed Compose configuration validation and a gateway image
  build. Current runs are available under the repository's **Actions** tab.
- `pip-audit` checked 23 resolved Python packages and found no known
  vulnerabilities. Container images were not vulnerability-scanned.
- Configuration YAML parsed; Kubernetes selectors, ports, ConfigMap references,
  and probes matched. All eight Grafana panels used the provisioned datasource.

## Local GPU and operations checks

Recorded on 14 October 2026 on WSL2 / Docker Desktop with an RTX 3060 12 GB,
using gateway 0.1.1:

- Real Qwen inference succeeded through Compose and Kubernetes gateways.
- During an inference outage, liveness returned 200, readiness 503, and chat 502.
- Prometheus targets and Grafana provisioning worked; `InferenceDown` fired,
  reached Alertmanager, and cleared after recovery.
- A bad Kubernetes upstream left the new Pod Running but not Ready. A direct
  request to that Pod returned 502; the old healthy Pod remained available.
  Rollback restored a successful Service chat request.

These hardware checks were not repeated in the independent gateway 0.1.2
review. Single chat requests show functionality, not benchmark performance.
Alertmanager has no external notification receiver. Kubernetes runs only the
gateway; inference and monitoring stay in Compose. See the README for startup,
verification commands, and cleanup.
