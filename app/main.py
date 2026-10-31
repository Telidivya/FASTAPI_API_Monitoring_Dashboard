import os
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

APP_NAME = "sample-fastapi-api"
START_TIME = time.time()

REQUESTS = Counter(
    "api_requests_total",
    "Total HTTP requests handled by the API",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "api_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 10),
)
IN_PROGRESS = Gauge("api_requests_in_progress", "Requests currently being processed")
APP_UP = Gauge("api_service_up", "Whether the application process is running")
APP_UP.set(1)

app = FastAPI(
    title="API Monitoring Demo",
    description="Sample REST API with Prometheus metrics and failure simulation endpoints.",
    version="1.0.0",
)

USERS = [
    {"id": 1, "name": "Asha", "email": "asha@example.com"},
    {"id": 2, "name": "Ravi", "email": "ravi@example.com"},
    {"id": 3, "name": "Meera", "email": "meera@example.com"},
]
PRODUCTS = [
    {"id": 101, "name": "Keyboard", "price": 799.0},
    {"id": 102, "name": "Mouse", "price": 399.0},
    {"id": 103, "name": "Monitor", "price": 8999.0},
]

_rate_lock = Lock()
_rate_events = defaultdict(deque)
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "5"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
EXPECTED_TOKEN = os.getenv("DEMO_API_TOKEN", "demo-secret-token")


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    endpoint = request.url.path
    start = time.perf_counter()
    IN_PROGRESS.inc()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        # The response is returned as a 500 while preserving the failure metric.
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    finally:
        elapsed = time.perf_counter() - start
        REQUESTS.labels(request.method, endpoint, str(status_code)).inc()
        REQUEST_LATENCY.labels(request.method, endpoint).observe(elapsed)
        IN_PROGRESS.dec()


@app.get("/")
def root():
    return {
        "service": APP_NAME,
        "message": "API Monitoring Demo",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": APP_NAME,
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "timestamp": time.time(),
    }


@app.get("/users")
def get_users():
    return {"count": len(USERS), "users": USERS}


@app.get("/products")
def get_products():
    return {"count": len(PRODUCTS), "products": PRODUCTS}


@app.get("/protected")
def protected(authorization: str | None = Header(default=None)):
    """Demo authentication endpoint. Send Authorization: Bearer demo-secret-token."""
    expected = f"Bearer {EXPECTED_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"message": "Authenticated successfully", "data": {"access": "granted"}}


@app.get("/simulate-error")
def simulate_error():
    """Intentionally returns HTTP 500 so monitoring and alert rules can be tested."""
    raise HTTPException(status_code=500, detail="Simulated server error for monitoring test")


@app.get("/simulate-timeout")
async def simulate_timeout(delay: float = 4.0):
    """Intentionally delays response; default delay is above the 3-second alert threshold."""
    delay = max(0.0, min(delay, 15.0))
    import asyncio
    await asyncio.sleep(delay)
    return {"message": "Delayed response completed", "delay_seconds": delay}


@app.get("/simulate-rate-limit")
def simulate_rate_limit(request: Request):
    """Allow a small number of requests per client IP in the configured rolling window."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    with _rate_lock:
        events = _rate_events[client_ip]
        while events and now - events[0] > RATE_LIMIT_WINDOW_SECONDS:
            events.popleft()
        if len(events) >= RATE_LIMIT_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: max {RATE_LIMIT_REQUESTS} requests "
                       f"per {RATE_LIMIT_WINDOW_SECONDS} seconds.",
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
            )
        events.append(now)
    return {
        "message": "Request accepted",
        "remaining_requests": max(0, RATE_LIMIT_REQUESTS - len(events)),
        "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
    }


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/ready")
def ready():
    return {"status": "ready"}
