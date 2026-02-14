"""Tests for the circuit breaker module."""

import time
from unittest.mock import patch

from core.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure(Exception("err"))
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure(Exception("err"))
        cb.record_failure(Exception("err"))
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_success_resets_failures(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure(Exception("err"))
        cb.record_failure(Exception("err"))
        cb.record_success()
        assert cb._failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_transitions_to_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure(Exception("err"))
        cb.record_failure(Exception("err"))
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.can_execute() is True

    def test_half_open_success_closes(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure(Exception("err"))
        cb.record_failure(Exception("err"))
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure(Exception("err"))
        cb.record_failure(Exception("err"))
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_failure(Exception("probe failed"))
        assert cb.state == CircuitState.OPEN

    def test_manual_reset(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        cb.record_failure(Exception("err"))
        cb.record_failure(Exception("err"))
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_repr(self):
        cb = CircuitBreaker("my_breaker", failure_threshold=5)
        r = repr(cb)
        assert "my_breaker" in r
        assert "closed" in r
