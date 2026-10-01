# Runbook: InferenceDown

## Meaning and impact

Prometheus has failed to scrape vLLM metrics for at least one minute.
This can indicate an inference failure or a connectivity/metrics problem.

If inference is unavailable:
- Gateway liveness remains HTTP 200.
- Gateway readiness returns HTTP 503.
- Chat requests return HTTP 502 when the upstream request fails.

## Diagnosis

Run from the project directory:

```bash
docker compose ps -a
docker compose logs --tail 100 inference
curl -i http://localhost:8000/health
curl -i http://localhost:8080/health/ready
```

For GPU-related errors, also check:

```bash
nvidia-smi
```

## Recovery

If the inference container is stopped:

```bash
docker compose start inference
```

If it is running but failing, inspect its logs and correct the cause.
Restart it after correcting the configuration when needed.

## Verification

- Inference health returns HTTP 200.
- Gateway readiness returns HTTP 200.
- Prometheus reports `up{job="vllm"} == 1`.
- InferenceDown returns to inactive in Prometheus and clears from
  Alertmanager's active alerts.
- A test chat request succeeds.

If inference works but the alert persists, inspect the vLLM target's
scrape error in Prometheus before restarting inference again.