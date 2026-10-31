# Submission Status and Verification Notes

This package includes:
- FastAPI sample endpoints and Prometheus instrumentation
- Prometheus scrape configuration and alert rules
- Blackbox Exporter health endpoint probe
- Grafana dashboard plus datasource/dashboard provisioning
- Alertmanager integration
- Pytest API tests and a smoke-test script
- Setup, troubleshooting, and interview documentation

Before submitting:
1. Run `pytest -q` in a Python virtual environment.
2. Run `python scripts/smoke_check.py` while the API is running locally.
3. Run `docker compose up --build -d` with Docker Desktop.
4. Confirm both targets in Prometheus `/targets` are UP.
5. Generate traffic and check the Grafana dashboard and Prometheus `/alerts`.
6. If the rubric requires actual email/Slack alert proof, configure a valid receiver in `monitoring/alertmanager.yml`, trigger an alert, and capture the received notification.

No screenshots or notification receipts are fabricated or included. Notification delivery is not enabled until a real receiver is configured.
