# Mini AI Platform

A small local portfolio project: a FastAPI gateway calls vLLM running
`Qwen/Qwen3-0.6B` on an NVIDIA GPU. Prometheus, Grafana, and Alertmanager
provide metrics, a dashboard, and one inference availability alert.
Docker Compose runs the stack; optional local Kubernetes runs the gateway.
This is a learning project, not a production-ready service. Cloud deployment
is outside the project's scope.

## Architecture

```text
Client -> FastAPI gateway -> vLLM -> Qwen3 model on GPU
              |               |
              +-- /metrics ---+ -> Prometheus -> Grafana
                                      |
                                 Alertmanager
```

The gateway validates a message, sends an OpenAI-compatible completion request,
and returns the answer, model, token usage, and upstream latency. It reuses one
HTTP client and logs JSON request metadata with an `X-Request-ID`. Prompt and
response content are not logged. Health checks and metrics are excluded from
request counters; request IDs are not metric labels.

## Prerequisites and configuration

- Windows with WSL2 and Docker Desktop using WSL integration, or a compatible
  Linux Docker installation with NVIDIA GPU support.
- An NVIDIA GPU with drivers visible to containers. Tested on an RTX 3060
  with 12 GB VRAM and a PC with 16 GB RAM.
- Docker Compose v2, `curl`, internet access for the initial images/model download.
- Optional: Docker Desktop local Kubernetes enabled and `kubectl`.

From the repository root, copy `.env.example` to `.env` **only if `.env` does
not already exist**, then set `GRAFANA_ADMIN_PASSWORD` to your own password.
`.env` is ignored by Git. The password initializes Grafana on a new volume;
changing it later does not reset an existing Grafana account.

Gateway configuration lives in `compose.yaml` (`k8s/gateway-config.yaml` for
Kubernetes): `VLLM_BASE_URL` and `MODEL_NAME`. `LOG_LEVEL` defaults to `INFO`.
The HTTP client timeout is 60 seconds; readiness has a 5-second timeout.
Keep the model name consistent with the inference command.

The existing vLLM configuration uses a 4096-token context and 80% GPU memory
utilization. `VLLM_WSL2_ENABLE_PIN_MEMORY=1` is retained for the tested WSL2
runtime. Hugging Face and vLLM caches are bind-mounted from
`$HOME/.cache/huggingface` and `$HOME/.cache/vllm`. The first start can take
several minutes; subsequent starts reuse model weights.

## Start and verify

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 inference
curl -f http://localhost:8000/health
curl -f http://localhost:8080/health/live
curl -f http://localhost:8080/health/ready
curl -f http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: demo-request' \
  -d '{"message":"Say hello in one short sentence.","max_tokens":32}'
```

`POST /chat` accepts `message` (1–4000 characters), `max_tokens` (1–512,
default 128), and `temperature` (0–2, default 0.2). Invalid input returns 422;
upstream errors, timeouts, and malformed responses return 502. Qwen thinking
is disabled for this simple chat endpoint.

| Endpoint | Purpose |
| --- | --- |
| `http://localhost:8080/docs` | Interactive gateway API documentation |
| `http://localhost:8080/health/live` | Gateway process responding (200) |
| `http://localhost:8080/health/ready` | Inference health reachable (200 or 503) |
| `http://localhost:8080/metrics` | Gateway Prometheus metrics |
| `http://localhost:9090/targets` | Scrape health; all four targets should be up |
| `http://localhost:3000` | Grafana; user `admin`, password from `.env` |
| `http://localhost:9093` | Alertmanager alerts |

Open Grafana's **Mini AI Platform** folder and **Mini AI Platform Overview**
dashboard. It shows availability, gateway request/error rates and P95 latency,
and vLLM token throughput, time to first token, cache use, and concurrency.
Generate requests and allow a few scrape intervals for rate graphs.
Monitoring ports bind to loopback. Gateway and inference retain their existing
port mappings; use this stack on a trusted local machine (no API authentication).

The `InferenceDown` rule fires after the vLLM metrics target has been down for
one minute. Alertmanager groups it but has no external notification receiver.
See [the recovery runbook](docs/runbooks/inference-down.md). For a local failure
drill, stop inference, observe live=200, ready=503, chat=502, wait for the alert,
then restart inference and confirm recovery:

```bash
docker compose stop inference
docker compose start inference
```

Leave enough time between those commands to observe the alert. Compose's
gateway health check deliberately uses liveness: it can remain healthy while
inference is unavailable. `depends_on` orders startup, not ongoing recovery.

## Optional local Kubernetes

Kubernetes runs only the gateway; inference and monitoring remain in Compose.
The manifest uses `host.docker.internal:8000` to reach Docker Desktop inference.
It is specific to this local setup. Prometheus's gateway target monitors the
Compose gateway, not the Kubernetes gateway.

```bash
docker build -t mini-ai-gateway:0.1.1 gateway
kubectl config current-context  # confirm docker-desktop before applying
kubectl apply -f k8s/
kubectl rollout status deployment/gateway -n mini-ai-platform --timeout=90s
kubectl get pods -n mini-ai-platform
kubectl port-forward -n mini-ai-platform service/gateway 8081:8080
```

In another terminal, verify `http://localhost:8081/health/ready` and send the
same chat request to port 8081. If using a different local cluster, load the
image into its runtime and configure a reachable host address.

To practice a failed rollout:

```bash
kubectl set env deployment/gateway -n mini-ai-platform VLLM_BASE_URL=http://127.0.0.1:8000
kubectl get pods -n mini-ai-platform
# Wait for the new Pod to run; it should stay 0/1 Ready.
# Port-forward that specific new Pod to inspect its 503 readiness and 502 chat.
kubectl rollout undo deployment/gateway -n mini-ai-platform
kubectl rollout status deployment/gateway -n mini-ai-platform --timeout=90s
kubectl apply -f k8s/
```

Inside a Pod, `127.0.0.1` points to that Pod, not the Compose inference server.
Readiness keeps the failed new Pod out of Service traffic; the rolling update
retains the old healthy Pod. A direct failing-Pod request is not evidence of a
Service-wide outage. Liveness prevents unnecessary restarts during upstream
failure. Use a new image tag when updating gateway code.

## Tests and CI

One GitHub Actions workflow runs on pushes and pull requests: Python syntax
checks, six focused `unittest` tests, dependency consistency, Compose validation,
and a gateway image build. Tests use `httpx.MockTransport` fixtures for success,
HTTP errors, connection failures, timeouts, malformed responses, validation,
health checks, request IDs, and metrics. No GPU, vLLM, or model downloads are
required. Real inference and rollback are verified separately on the local PC.

Run the same gateway tests with Docker:

```bash
docker build -t mini-ai-gateway:0.1.1 gateway
docker run --rm -v "$PWD/gateway/tests:/app/tests:ro" \
  mini-ai-gateway:0.1.1 python -m unittest discover -s tests -v
docker run --rm mini-ai-gateway:0.1.1 python -m pip check
```

For a Python 3.12 virtual environment, install `gateway/requirements.txt`, then
run `python -m unittest discover -s tests -v` from `gateway/`.
Actual executed results are recorded in [verification notes](docs/verification.md).
Historical experiments and interview topics are in [engineering notes](docs/interview-notes.md).

## Troubleshooting and cleanup

- GPU/startup failures: inspect inference logs and run
  `docker compose exec inference nvidia-smi`. Close other GPU-heavy programs
  if memory is exhausted; don't delete caches to fix unrelated failures.
- Gateway 502/503: check upstream health and `VLLM_BASE_URL`; correlate logs with
  the returned request ID. A malformed upstream result is also a 502.
- Prometheus/Grafana missing files after a WSL/Docker restart: inspect logs and
  mounted files. `docker compose up -d --force-recreate prometheus grafana alertmanager`
  refreshes bind mounts while retaining named volumes. Check system time if
  Prometheus reports out-of-order samples.
- Grafana password: an existing volume retains the original login. Use Grafana's
  password-change/reset facility rather than deleting the volume.
- Kubernetes: inspect `kubectl describe pod`, logs, readiness, and rollout history;
  a Running Pod is not necessarily Ready.

```bash
docker compose stop                 # keep containers, caches, and volumes
# Or remove containers/network while retaining persistent data:
docker compose down
# Optional: remove only the project's local Kubernetes resources:
kubectl delete -f k8s/
```

Do not use `docker compose down -v` or prune volumes/caches for routine cleanup.
The project is complete as a local learning demo; cloud deployment and external
alert notifications are not implemented or required.
