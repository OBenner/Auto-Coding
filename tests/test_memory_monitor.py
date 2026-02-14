"""Tests for the memory monitor module."""

from unittest.mock import MagicMock, patch

from core.memory_monitor import MemoryMonitor, MemoryPressure, SessionBounds


class TestMemoryMonitor:
    def test_default_thresholds(self):
        mm = MemoryMonitor()
        assert mm._max_memory_mb == 2048.0
        assert mm._warning_threshold == 0.8

    def test_custom_thresholds(self):
        mm = MemoryMonitor(max_memory_mb=1024.0, warning_threshold=0.7)
        assert mm._max_memory_mb == 1024.0
        assert mm._warning_threshold == 0.7

    @patch("core.memory_monitor._PSUTIL_AVAILABLE", False)
    def test_no_psutil_returns_normal(self):
        mm = MemoryMonitor()
        mm._process = None
        assert mm.check_pressure() == MemoryPressure.NORMAL
        assert mm.get_usage_mb() == -1.0
        assert not mm.should_gc()

    def test_normal_pressure(self):
        mm = MemoryMonitor(max_memory_mb=2048.0)
        # Mock process with low memory usage
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(
            rss=500 * 1024 * 1024  # 500 MB
        )
        mm._process = mock_process
        assert mm.check_pressure() == MemoryPressure.NORMAL
        assert not mm.should_gc()

    def test_warning_pressure(self):
        mm = MemoryMonitor(max_memory_mb=1000.0, warning_threshold=0.8)
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(
            rss=850 * 1024 * 1024  # 850 MB — 85% of 1000 MB
        )
        mm._process = mock_process
        assert mm.check_pressure() == MemoryPressure.WARNING
        assert mm.should_gc()

    def test_critical_pressure(self):
        mm = MemoryMonitor(max_memory_mb=1000.0)
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(
            rss=1100 * 1024 * 1024  # 1100 MB — 110% of 1000 MB
        )
        mm._process = mock_process
        assert mm.check_pressure() == MemoryPressure.CRITICAL
        assert mm.should_gc()

    def test_maybe_gc_runs_when_needed(self):
        mm = MemoryMonitor(max_memory_mb=1000.0)
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=900 * 1024 * 1024)
        mm._process = mock_process
        with patch("core.memory_monitor.gc.collect") as mock_gc:
            result = mm.maybe_gc()
            assert result is True
            mock_gc.assert_called_once()


class TestSessionBounds:
    def test_under_bounds(self):
        assert not SessionBounds.check(10, 50)

    def test_rounds_exceeded(self):
        assert SessionBounds.check(100, 50)

    def test_messages_exceeded(self):
        assert SessionBounds.check(10, 500)

    def test_both_exceeded(self):
        assert SessionBounds.check(100, 500)

    def test_reason_rounds(self):
        reason = SessionBounds.reason(100, 50)
        assert "rounds" in reason
        assert "100" in reason

    def test_reason_messages(self):
        reason = SessionBounds.reason(10, 500)
        assert "messages" in reason
        assert "500" in reason

    def test_reason_empty_when_ok(self):
        assert SessionBounds.reason(10, 50) == ""
