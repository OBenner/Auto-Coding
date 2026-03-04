"""
Circuit Breaker
===============

Implements the circuit breaker pattern to prevent repeated calls to a
failing service.  After *failure_threshold* consecutive failures the
circuit opens and all subsequent calls are rejected until
*recovery_timeout* seconds have elapsed, at which point it enters a
half-open state allowing one probe call.
"""

import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Simple circuit breaker for API calls."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
    ) -> None:
        self.name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        """Return the current effective state (may transition from OPEN → HALF_OPEN)."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info(
                    "Circuit breaker '%s' transitioned to HALF_OPEN after %.1fs",
                    self.name,
                    elapsed,
                )
        return self._state

    def can_execute(self) -> bool:
        """Return True if the circuit allows a call to proceed."""
        current = self.state
        if current == CircuitState.CLOSED:
            return True
        if current == CircuitState.HALF_OPEN:
            return True  # Allow one probe call
        return False  # OPEN — reject

    def record_success(self) -> None:
        """Record a successful call — resets the breaker to CLOSED."""
        if self._state != CircuitState.CLOSED:
            logger.info(
                "Circuit breaker '%s' recovered → CLOSED",
                self.name,
            )
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self, error: Exception | None = None) -> None:
        """Record a failed call — may trip the breaker to OPEN."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            # Probe failed — reopen
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker '%s' probe failed → OPEN (error: %s)",
                self.name,
                error,
            )
        elif self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker '%s' tripped → OPEN after %d failures (error: %s)",
                self.name,
                self._failure_count,
                error,
            )

    def reset(self) -> None:
        """Manually reset the breaker to CLOSED."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(name={self.name!r}, state={self.state.value}, "
            f"failures={self._failure_count}/{self._failure_threshold})"
        )
