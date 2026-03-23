"""
Prometheus Metrics API route

Exposes application metrics in Prometheus text format at /metrics.
Suitable for scraping by Prometheus or compatible monitoring systems.
"""

import logging
import os
import time

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

logger = logging.getLogger(__name__)

# Record startup time for uptime gauge
_START_TIME: float = time.time()

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

# Application info (static labels – version, headless mode, etc.)
APP_INFO = Info(
    "auto_claude_app",
    "Auto Claude web-backend application information",
)

# Uptime gauge – updated on each /metrics scrape
UPTIME_SECONDS = Gauge(
    "auto_claude_uptime_seconds",
    "Seconds elapsed since the web-backend process started",
)

# HTTP request counter (labelled by method, endpoint, and HTTP status code)
HTTP_REQUESTS_TOTAL = Counter(
    "auto_claude_http_requests_total",
    "Total number of HTTP requests handled",
    ["method", "endpoint", "status_code"],
)

# HTTP request latency histogram
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "auto_claude_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Agent task gauges
AGENT_TASKS_ACTIVE = Gauge(
    "auto_claude_agent_tasks_active",
    "Number of currently running agent tasks",
)

AGENT_TASKS_TOTAL = Counter(
    "auto_claude_agent_tasks_total",
    "Total number of agent tasks started",
    ["status"],  # labels: started, completed, failed, cancelled
)

# Create router – no authentication required for metrics (scraper access)
router = APIRouter(prefix="/metrics", tags=["metrics"])


def _collect_agent_task_metrics() -> None:
    """Update agent task gauges from the agent runner service."""
    try:
        from services.agent_runner import get_all_task_statuses

        statuses = get_all_task_statuses()
        active = sum(
            1
            for s in statuses.values()
            if s.get("status") in ("running", "pending")
        )
        AGENT_TASKS_ACTIVE.set(active)
    except Exception as exc:  # pragma: no cover
        logger.debug("Could not collect agent task metrics: %s", exc)
        # Leave gauge at its last known value rather than resetting


@router.get(
    "",
    summary="Prometheus metrics",
    description=(
        "Exposes application metrics in Prometheus text exposition format. "
        "Intended to be scraped by a Prometheus server or compatible agent."
    ),
    response_class=PlainTextResponse,
)
async def metrics() -> PlainTextResponse:
    """
    Prometheus metrics endpoint.

    Returns all registered metrics in the Prometheus text exposition format
    (``text/plain; version=0.0.4``).  The endpoint is unauthenticated so
    that Prometheus scrapers can reach it without credentials.

    Exposed metrics:
    - ``auto_claude_app_info``          – static application labels (version, headless)
    - ``auto_claude_uptime_seconds``    – process uptime in seconds
    - ``auto_claude_http_requests_total``            – HTTP request counts by method/endpoint/status
    - ``auto_claude_http_request_duration_seconds``  – HTTP latency histogram
    - ``auto_claude_agent_tasks_active``             – currently running agent tasks
    - ``auto_claude_agent_tasks_total``              – lifetime agent task counts by status

    Example:
        ```bash
        curl http://localhost:8000/metrics
        # Returns Prometheus text format metrics
        ```
    """
    headless_mode = (
        os.getenv("HEADLESS", "false").lower() == "true"
        or os.getenv("AUTO_CLAUDE_HEADLESS", "false").lower() == "true"
    )

    # Update dynamic metrics before generating output
    UPTIME_SECONDS.set(round(time.time() - _START_TIME, 3))
    APP_INFO.info(
        {
            "version": "1.0.0",
            "headless_mode": str(headless_mode).lower(),
        }
    )
    _collect_agent_task_metrics()

    output = generate_latest()
    return PlainTextResponse(
        content=output.decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
