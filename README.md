# FastAPI API Monitoring Dashboard Demo

A runnable sample REST API with Prometheus metrics, Grafana dashboard provisioning, alert rules, failure simulation, tests, and troubleshooting notes.

## 1. Architecture

- **FastAPI** serves sample endpoints and exposes request metrics at `/metrics`.
- **Prometheus** scrapes `/metrics` every 5 seconds and evaluates alert rules.
- **Blackbox Exporter** actively probes the `/health` endpoint over HTTP.
- **Grafana** reads Prometheus and loads the preconfigured dashboard.
- **Alertmanager** receives firing alerts. Email/Slack delivery requires you to configure a real SMTP server or webhook.
- **pytest / smoke test** validate normal and failure paths.

> This demo intentionally uses simulated failures. Do not expose it publicly or use the demo token in production.

## 2. Run locally without Docker (Windows)

Open PowerShell in this project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- Metrics: http://127.0.0.1:8000/metrics

In a second terminal, run `python scripts/smoke_check.py`. For unit tests run `pytest -q`.

## 3. Run full monitoring stack with Docker

Install and start Docker Desktop first. From the project directory:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

Open:
- FastAPI docs: http://localhost:8000/docs
- Prometheus targets: http://localhost:9090/targets
- Prometheus alerts: http://localhost:9090/alerts
- Grafana: http://localhost:3000 (user `admin`, password from `.env`)
- Alertmanager: http://localhost:9093

The Grafana dashboard is provisioned automatically. Select **Dashboards → API Monitoring → FastAPI API Monitoring**.

To stop the stack: `docker compose down`. To remove Grafana's stored data too: `docker compose down -v`.

## 4. Metrics and dashboard

Metrics emitted:
- `api_requests_total{method, endpoint, status_code}` — total requests, grouped by route and response status.
- `api_request_duration_seconds` — request latency histogram.
- `api_requests_in_progress` — requests currently being processed.
- `api_service_up` — application-process indicator.
- Prometheus `up{job="fastapi"}` — whether Prometheus can scrape the API.

Dashboard panels include total requests, request failure count, average latency, p95 latency, request rate, HTTP status-code distribution, and service scrape health. The error-rate query treats both 4xx and 5xx as failed responses; this is useful for the demo but should be aligned with service-specific SLOs in production.

## 5. Failure simulation and root-cause notes

| Scenario | How to trigger | Expected result | Likely interpretation |
|---|---|---|---|
| Authentication failure | `GET /protected` without Authorization | HTTP 401; failure metrics increase | Missing/invalid Bearer token; check client credentials and auth header |
| Server error | `GET /simulate-error` | HTTP 500; `APIHTTP500Errors` can fire | Deliberate exception; inspect logs and trace/request context |
| Slow response | `GET /simulate-timeout?delay=4` | Response takes about 4 seconds; latency histogram increases | Simulated dependency/network delay; compare route latency and dependency timing |
| Rate limit | Call `/simulate-rate-limit` more than 5 times in 60 seconds | HTTP 429 and `Retry-After` header | Client exceeded configured limit; check retry strategy and request volume |
| Service down | Stop the API container/process | Prometheus `up{job="fastapi"}` becomes 0; `APIServiceDown` can fire | Process/container unavailable, port/network/config issue |

For an easy rate-limit demo, use the smoke test or click `/simulate-rate-limit` repeatedly in `/docs`. The limit is per client IP and configurable through environment variables.

## 6. Alert rules

Rules are in `monitoring/alert_rules.yml`:
- **APIServiceDown** — scrape target is down for 15 seconds.
- **APIHighResponseTime** — p95 latency exceeds 3 seconds for 30 seconds.
- **APIHTTP500Errors** — HTTP 500 responses are observed.
- **APIHighFailureRate** — more than 20% of recent requests return 4xx/5xx.
- **APIHealthEndpointFailing** — fires when Blackbox Exporter cannot get HTTP 200 from `/health`.

Alert rules evaluate on a time window and `for` duration, so a single request may not instantly produce an alert. Generate a small burst of failures and allow Prometheus to evaluate.

### Configure email or Slack notifications

Alertmanager is wired into Prometheus, but notification delivery is not configured by default because credentials are personal secrets. Edit `monitoring/alertmanager.yml`:
- For email, uncomment `email_configs` and enter your SMTP host, sender, recipient, and authentication details.
- For Slack, uncomment `slack_configs` and add a Slack Incoming Webhook URL.
- Restart Alertmanager: `docker compose restart alertmanager`.

Do not commit `.env`, webhook URLs, SMTP passwords, or production tokens to Git.

## 7. Validation checklist

1. `/health`, `/users`, `/products` return HTTP 200.
2. `/protected` returns 401 without a token and 200 with the demo Bearer token.
3. `/simulate-error` returns HTTP 500.
4. `/simulate-timeout?delay=4` takes more than 3 seconds.
5. Repeated `/simulate-rate-limit` requests eventually return HTTP 429.
6. `/metrics` contains `api_requests_total` and `api_request_duration_seconds`.
7. Prometheus `/targets` shows both the FastAPI metrics target and the FastAPI health probe as UP.
8. Grafana dashboard panels populate after traffic has been generated.
9. Prometheus `/alerts` shows the configured alert state when the rule conditions persist.
10. After configuring real notification credentials, verify a notification in the destination and document the result.

## 8. Troubleshooting

- **Prometheus target DOWN:** check `docker compose ps`, API container logs (`docker compose logs api`), and that the target is `api:8000` from inside the Docker network.
- **Empty Grafana panels:** generate traffic, wait at least one scrape interval, and verify Prometheus queries in Explore.
- **No alert yet:** confirm the expression is true and wait for the rule's `for` period; inspect Prometheus `/alerts`.
- **No email/Slack message:** Alertmanager has no real receiver configured by default. Configure SMTP/webhook and inspect `docker compose logs alertmanager`.
- **Port already in use:** stop the process using 8000, 9090, 9093, or 3000, or adjust the port mapping in `docker-compose.yml`.
- **PowerShell activation blocked:** run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate the venv.

## 9. Maintenance

- Pin dependency/image versions and update them after testing.
- Keep tokens and notification credentials in a secret manager or local `.env` excluded from Git.
- Review alert thresholds against expected traffic and false-positive rates.
- Retain only useful labels; avoid user IDs, emails, or other high-cardinality/sensitive values in metrics.
- Add structured logs, request IDs, tracing, and dependency-level metrics before production use.

## 10. Project limitations

This is a demo/reference implementation, not a production monitoring platform. It does not include persistent API data, a distributed rate limiter, real authentication, automatic Blackbox probing, or configured external notification credentials. Alert delivery must be verified after you add your own receiver settings.


## 11. Health probe

The Docker stack includes Blackbox Exporter at `http://localhost:9115`. Prometheus probes `http://api:8000/health` through the `fastapi-health` scrape job. The `APIHealthEndpointFailing` rule is therefore active when the probe returns failure. If the whole API is stopped, both the metrics scrape and health probe should fail.

## 12. Quick commands

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f api
docker compose logs -f prometheus
docker compose down
```
