# Local verification — 14 October 2026

Executed on the existing WSL2 / Docker Desktop PC with an RTX 3060 12 GB.
No cloud resources were assessed or provisioned. Existing caches and named
volumes were retained.

| Check | Actual result |
| --- | --- |
| Gateway Docker image build | Passed with existing pinned direct dependencies |
| Six gateway fixture tests | Passed: success, HTTP/connect/timeout failures, malformed responses, validation, health, IDs, metrics |
| Python syntax compilation | Passed; container check uses `/tmp` for bytecode because application files and the test mount are read-only to its user |
| `pip check` | Passed, no broken requirements |
| `docker compose config --quiet` | Passed |
| Real GPU inference | Passed through Compose gateway; Qwen returned an answer and token usage; container `nvidia-smi` confirmed RTX 3060 |
| Gateway health during inference outage | Passed: liveness 200, readiness 503, chat 502 |
| Prometheus config and alert rules | Passed `promtool check config`; all four scrape targets up before outage |
| Alertmanager config | Passed `amtool check-config` |
| Grafana dashboard and data source | Passed authenticated API checks: provisioned dashboard found, Prometheus query succeeded |
| InferenceDown firing | Passed after stopping inference; alert received by Alertmanager |
| Inference recovery | Passed: readiness 200, four targets up, alert inactive and cleared in Alertmanager, real chat succeeded |
| Local Kubernetes updated gateway | Passed rollout with image `mini-ai-gateway:0.1.1` |
| Kubernetes bad upstream / rollback | Passed: bad Pod Running 0/1 Ready, live 200, ready 503, direct chat 502; old Pod ready 200; rollback successful |
| Kubernetes Service chat after rollback | Passed through local port-forward; real Qwen response returned |
| Secret review | No current secret-pattern candidates or historical private-key/GitHub-token candidates; `.env` ignored; old example Grafana password invalidated by local rotation |
| GitHub Actions | Passed: [initial push run](https://github.com/Basmuta/mini-ai-platform/actions/runs/38518582151), including syntax, six tests, dependency check, Compose validation, and image build |

## Issues found and resolved

- Malformed upstream JSON/completion fields previously escaped as internal
  errors. Gateway now returns a controlled 502; fixtures cover this behavior.
- Prometheus and Alertmanager were stopped on arrival. Restarted them. Grafana
  initially had an empty stale bind mount after WSL restart (dashboard API 404).
  Recreating monitoring containers restored file mounts and dashboard provisioning
  without removing persistent volumes.
- The example password matched the local Grafana password. Replaced the example,
  rotated the real login through Grafana, and updated only the ignored `.env`.
  Historical commits retain the now-invalid example; history was not rewritten.
- An initial container `compileall` attempt failed because it tried to write
  bytecode to read-only files. Re-ran successfully with
  `PYTHONPYCACHEPREFIX=/tmp/pycache`; the GitHub checkout is writable.

## Limits

Single real chat requests demonstrate functionality, not a performance benchmark.
Alertmanager has a local empty receiver; no email/chat notification was tested.
Kubernetes tests target Docker Desktop, with inference outside the cluster.
GPU behavior is verified locally and deliberately excluded from CI.

## Repository review and gateway 0.1.2

An independent review of published commit `7de7b9b` checked all project files
and 10 commits (40 distinct file versions). No tracked `.env`, API-token,
or private-key candidates were found. The historical default Grafana password
remains in Git; its rotation is recorded above and was not independently
rechecked against the local Grafana instance.

The old FastAPI pin resolved Starlette 0.47.3 with known security advisories.
A malformed Host header also reproduced a concrete gateway issue: a successful
`/chat` request could be omitted from logs and request counters. Logging and
metric exclusions now use the actual ASGI path. FastAPI 0.133.0 and Starlette
1.3.1 are pinned to compatible patched versions, and a regression test covers
the missing log/counter case.

Rechecked in an isolated Python 3.12 environment:

- All seven gateway tests passed, including the malformed Host regression.
- Python syntax compilation and `pip check` passed.
- `pip-audit -r gateway/requirements.txt` checked 23 resolved Python packages
  and reported no known vulnerabilities on 14 October 2026. Container images
  were not vulnerability-scanned.
- All 10 YAML configuration files parsed; Kubernetes namespace, selectors,
  Service ports, ConfigMap references, and probe settings were consistent.
- The Grafana dashboard JSON parsed and all eight panels referenced the
  provisioned Prometheus datasource.

Docker Desktop, GPU inference, alert firing/recovery, and Kubernetes rollback
were not rerun in this review environment. The earlier local results above
apply to gateway 0.1.1. After pulling the changes, rebuild the Compose gateway;
for Kubernetes, build `mini-ai-gateway:0.1.2` and reapply `k8s/` as documented
in the README. The new image tag avoids reusing the previous cached gateway.
