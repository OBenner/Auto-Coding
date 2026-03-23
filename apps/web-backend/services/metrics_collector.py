"""
Metrics Collector Service

Service layer for collecting and exposing Prometheus metrics for the web backend.
Tracks agent run counts, error rates, and latency histograms for observability.
"""

import logging
import time
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


def _sanitize_log(value: str) -> str:
    """Sanitize value for safe logging (prevent log injection)."""
    return str(value).replace("\n", "\\n").replace("\r", "\\r")


def _try_import_prometheus():
    """
    Attempt to import prometheus_client, returning None if unavailable.

    Returns:
        The prometheus_client module or None if not installed
    """
    try:
        import prometheus_client

        return prometheus_client
    except ImportError:
        logger.warning(
            "prometheus_client not installed. Metrics collection disabled. "
            "Install with: pip install prometheus-client"
        )
        return None


class MetricsCollector:
    """
    Service for collecting Prometheus metrics for agent operations.

    Tracks:
    - Agent run counts (by agent type and status)
    - Error counts (by agent type and error type)
    - Agent run latency histograms (by agent type)
    - Active agent run gauges (by agent type)

    Gracefully degrades if prometheus_client is not installed.
    """

    def __init__(self, registry=None):
        """
        Initialize metrics collector with Prometheus counters and histograms.

        Args:
            registry: Optional Prometheus registry. Defaults to the global registry.
                      Pass a CollectorRegistry() instance for isolated testing.
        """
        self._prometheus = _try_import_prometheus()
        self._enabled = self._prometheus is not None
        self._registry = registry

        if self._enabled:
            self._init_metrics()
            logger.info("MetricsCollector initialized with Prometheus metrics")
        else:
            self._agent_runs_total = None
            self._agent_errors_total = None
            self._agent_run_latency_seconds = None
            self._active_agent_runs = None
            logger.warning(
                "MetricsCollector initialized without Prometheus (metrics disabled)"
            )

    def _init_metrics(self) -> None:
        """Initialize all Prometheus metrics counters, histograms, and gauges."""
        pc = self._prometheus
        kwargs = {"registry": self._registry} if self._registry is not None else {}

        # Counter: total agent runs by agent_type and status
        self._agent_runs_total = pc.Counter(
            "auto_claude_agent_runs_total",
            "Total number of agent runs",
            ["agent_type", "status"],
            **kwargs,
        )

        # Counter: total agent errors by agent_type and error_type
        self._agent_errors_total = pc.Counter(
            "auto_claude_agent_errors_total",
            "Total number of agent errors",
            ["agent_type", "error_type"],
            **kwargs,
        )

        # Histogram: agent run latency in seconds by agent_type
        self._agent_run_latency_seconds = pc.Histogram(
            "auto_claude_agent_run_latency_seconds",
            "Agent run latency in seconds",
            ["agent_type"],
            buckets=[1, 5, 10, 30, 60, 120, 300, 600, float("inf")],
            **kwargs,
        )

        # Gauge: currently active agent runs by agent_type
        self._active_agent_runs = pc.Gauge(
            "auto_claude_active_agent_runs",
            "Number of currently active agent runs",
            ["agent_type"],
            **kwargs,
        )

    def record_agent_run_start(self, agent_type: str) -> None:
        """
        Record the start of an agent run.

        Increments the active agent runs gauge for the given agent type.

        Args:
            agent_type: Type of agent (e.g., "planner", "coder", "qa_reviewer", "qa_fixer")
        """
        if not self._enabled:
            return

        try:
            self._active_agent_runs.labels(agent_type=agent_type).inc()
            logger.debug(
                f"Recorded agent run start: {_sanitize_log(agent_type)}"
            )
        except Exception as e:
            logger.error(f"Failed to record agent run start metric: {e}")

    def record_agent_run_end(
        self, agent_type: str, status: str, duration_seconds: float
    ) -> None:
        """
        Record the end of an agent run with status and duration.

        Increments the run counter, decrements the active gauge,
        and observes the latency histogram.

        Args:
            agent_type: Type of agent (e.g., "planner", "coder", "qa_reviewer", "qa_fixer")
            status: Completion status ("success", "failure", "cancelled")
            duration_seconds: Duration of the run in seconds
        """
        if not self._enabled:
            return

        try:
            self._agent_runs_total.labels(
                agent_type=agent_type, status=status
            ).inc()
            self._active_agent_runs.labels(agent_type=agent_type).dec()
            self._agent_run_latency_seconds.labels(agent_type=agent_type).observe(
                duration_seconds
            )
            logger.debug(
                f"Recorded agent run end: {_sanitize_log(agent_type)}, "
                f"status={_sanitize_log(status)}, duration={duration_seconds:.2f}s"
            )
        except Exception as e:
            logger.error(f"Failed to record agent run end metric: {e}")

    def record_agent_error(self, agent_type: str, error_type: str) -> None:
        """
        Record an agent error occurrence.

        Args:
            agent_type: Type of agent (e.g., "planner", "coder", "qa_reviewer", "qa_fixer")
            error_type: Category of error (e.g., "timeout", "auth_error", "system_error",
                        "build_failed", "qa_failed")
        """
        if not self._enabled:
            return

        try:
            self._agent_errors_total.labels(
                agent_type=agent_type, error_type=error_type
            ).inc()
            logger.debug(
                f"Recorded agent error: {_sanitize_log(agent_type)}, "
                f"type={_sanitize_log(error_type)}"
            )
        except Exception as e:
            logger.error(f"Failed to record agent error metric: {e}")

    @contextmanager
    def track_agent_run(
        self, agent_type: str
    ) -> Generator[None, None, None]:
        """
        Context manager to automatically track an agent run's duration and status.

        Records start, end, latency, and errors automatically.

        Args:
            agent_type: Type of agent being tracked

        Yields:
            None

        Example:
            with metrics.track_agent_run("coder"):
                result = await run_coder_agent(...)
        """
        self.record_agent_run_start(agent_type)
        start_time = time.monotonic()
        status = "success"

        try:
            yield
        except Exception as e:
            status = "failure"
            error_type = type(e).__name__
            self.record_agent_error(agent_type, error_type)
            raise
        finally:
            duration = time.monotonic() - start_time
            self.record_agent_run_end(agent_type, status, duration)

    def get_metrics_output(self) -> tuple[bytes, str]:
        """
        Generate Prometheus metrics output for the /metrics endpoint.

        Returns:
            Tuple of (output_bytes, content_type) suitable for HTTP response.
            Returns empty bytes and text/plain if Prometheus is not available.
        """
        if not self._enabled:
            return b"# Prometheus metrics not available\n", "text/plain"

        try:
            pc = self._prometheus
            registry = self._registry if self._registry is not None else pc.REGISTRY
            output = pc.generate_latest(registry)
            content_type = pc.CONTENT_TYPE_LATEST
            return output, content_type
        except Exception as e:
            logger.error(f"Failed to generate Prometheus metrics output: {e}")
            return b"# Error generating metrics\n", "text/plain"

    @property
    def is_enabled(self) -> bool:
        """Whether Prometheus metrics collection is active."""
        return self._enabled
