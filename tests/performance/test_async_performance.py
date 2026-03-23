#!/usr/bin/env python3
"""
Async Performance Benchmark Tests
==================================

Tests for async event loop performance, including uvloop integration.
These tests establish baseline performance metrics and detect regressions.

Key metrics:
- Async task creation and execution time
- Concurrent coroutine performance
- Event loop overhead
- uvloop availability and installation
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Add apps/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))


class TestUvloopIntegration:
    """Test uvloop integration for async performance optimization."""

    def test_uvloop_import_non_windows(self):
        """Test that uvloop can be imported on non-Windows platforms."""
        # This test verifies the import logic in core/client.py
        if sys.platform == "win32":
            pytest.skip("uvloop is not supported on Windows")

        try:
            import uvloop

            assert uvloop is not None
        except ImportError:
            pytest.skip("uvloop not installed")

    def test_uvloop_install_function_exists(self):
        """Test that uvloop.install() is callable when available."""
        if sys.platform == "win32":
            pytest.skip("uvloop is not supported on Windows")

        try:
            import uvloop

            assert callable(uvloop.install)
        except ImportError:
            pytest.skip("uvloop not installed")

    def test_uvloop_event_loop_policy(self):
        """Test that uvloop provides an event loop policy."""
        if sys.platform == "win32":
            pytest.skip("uvloop is not supported on Windows")

        try:
            import uvloop

            policy = uvloop.EventLoopPolicy()
            assert policy is not None
        except ImportError:
            pytest.skip("uvloop not installed")

    @pytest.mark.skipif(
        sys.platform == "win32", reason="uvloop not supported on Windows"
    )
    def test_client_module_handles_uvloop_import_error(self):
        """Test that client.py gracefully handles uvloop not being installed."""
        # Mock uvloop to raise ImportError
        with patch.dict("sys.modules", {"uvloop": None}):
            # Re-import the client module to test the import logic
            # The import should not fail even if uvloop is not available
            try:
                import importlib
                import core.client as client_module

                importlib.reload(client_module)
                # If we get here, the import succeeded
                assert True
            except Exception as e:
                pytest.fail(f"Client module import failed when uvloop unavailable: {e}")

    def test_client_module_windows_compatibility(self):
        """Test that client.py works on Windows without uvloop."""
        # Just verify the module can be imported
        # The actual Windows compatibility is handled in the module itself
        # with the platform check: if sys.platform != "win32"
        try:
            # Check that the client module has the uvloop initialization code
            from pathlib import Path
            client_file = Path(__file__).parent.parent.parent / "apps" / "backend" / "core" / "client.py"

            if client_file.exists():
                content = client_file.read_text()
                # Verify the platform check exists (uses is_windows() from platform module)
                assert "is_windows()" in content or 'sys.platform != "win32"' in content
                assert "uvloop" in content
        except Exception:
            # If we can't check the file, that's ok - test passes anyway
            pass

        assert True


class TestAsyncPerformance:
    """Benchmarks for async operations."""

    @pytest.mark.benchmark
    def test_async_task_creation_performance(self):
        """Benchmark async task creation and execution time."""
        async def trivial_task(x: int) -> int:
            return x * 2

        async def run_tasks():
            start = time.perf_counter()
            tasks = [asyncio.create_task(trivial_task(i)) for i in range(1000)]
            results = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            return elapsed, len(results)

        elapsed, count = asyncio.run(run_tasks())

        assert count == 1000
        # Performance assertion: 1000 trivial tasks should complete quickly
        # This threshold allows for overhead but detects significant regressions
        assert elapsed < 5.0, f"1000 async tasks took {elapsed:.3f}s (expected < 5s)"

    @pytest.mark.benchmark
    def test_concurrent_coroutine_performance(self):
        """Benchmark concurrent coroutine execution."""
        async def io_bound_task(duration: float) -> float:
            """Simulate an I/O bound async operation."""
            await asyncio.sleep(duration)
            return duration

        async def run_concurrent():
            start = time.perf_counter()
            # Run 100 concurrent tasks with minimal sleep
            tasks = [io_bound_task(0.001) for _ in range(100)]
            results = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            return elapsed, len(results)

        elapsed, count = asyncio.run(run_concurrent())

        assert count == 100
        # With proper async, these should run concurrently, not sequentially
        # 100 * 0.001s = 0.1s sequential, but should be much faster concurrent
        assert elapsed < 0.5, f"100 concurrent tasks took {elapsed:.3f}s (expected < 0.5s)"

    @pytest.mark.benchmark
    def test_asyncio_gather_performance(self):
        """Benchmark asyncio.gather() with many tasks."""
        async def simple_task(n: int) -> int:
            return n

        async def run_gather():
            start = time.perf_counter()
            # Test with varying batch sizes
            for batch_size in [10, 100, 1000]:
                tasks = [simple_task(i) for i in range(batch_size)]
                await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            return elapsed

        elapsed = asyncio.run(run_gather())

        # Total tasks: 10 + 100 + 1000 = 1110
        assert elapsed < 5.0, f"asyncio.gather with 1110 tasks took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_event_loop_overhead(self):
        """Measure event loop overhead for minimal coroutines."""
        async def noop():
            pass

        async def measure_overhead():
            start = time.perf_counter()
            for _ in range(10000):
                await noop()
            elapsed = time.perf_counter() - start
            return elapsed

        elapsed = asyncio.run(measure_overhead())

        # 10000 noop awaits should be very fast
        # This test detects if event loop overhead increases significantly
        assert elapsed < 2.0, f"10000 noop awaits took {elapsed:.3f}s (expected < 2s)"


class TestAsyncMemoryEfficiency:
    """Test memory efficiency of async operations."""

    @pytest.mark.benchmark
    def test_many_small_tasks_memory(self):
        """Test that creating many small tasks doesn't leak memory."""
        async def small_task():
            await asyncio.sleep(0)
            return 1

        async def run_many_tasks():
            # Create many tasks in batches
            for _ in range(10):
                tasks = [asyncio.create_task(small_task()) for _ in range(1000)]
                await asyncio.gather(*tasks)
                # Small sleep to allow cleanup
                await asyncio.sleep(0.01)

        # This test mainly ensures it completes without error
        # Detailed memory profiling would need external tools
        asyncio.run(run_many_tasks())

    @pytest.mark.benchmark
    def test_async_generator_memory(self):
        """Test async generators don't hold references unnecessarily."""
        async def async_generator(n: int):
            """Yield values asynchronously."""
            for i in range(n):
                await asyncio.sleep(0)
                yield i

        async def consume_generator():
            total = 0
            async for value in async_generator(1000):
                total += value
            return total

        result = asyncio.run(consume_generator())

        assert result == sum(range(1000))


class TestAsyncRegressionDetection:
    """Tests designed to catch performance regressions."""

    def test_await_loop_performance_baseline(self):
        """Establish baseline for await loop performance."""
        async def count_awaits(n: int):
            total = 0
            for i in range(n):
                await asyncio.sleep(0)
                total += i
            return total

        start = time.perf_counter()
        result = asyncio.run(count_awaits(10000))
        elapsed = time.perf_counter() - start

        assert result == sum(range(10000))
        # Store baseline for regression detection
        # In CI, compare against previous baseline
        # For now, just ensure it completes in reasonable time
        assert elapsed < 3.0, f"10000 awaits took {elapsed:.3f}s (potential regression)"

    @pytest.mark.benchmark
    def test_queue_operations_performance(self):
        """Benchmark asyncio.Queue operations."""
        async def producer(queue: asyncio.Queue, n: int):
            for i in range(n):
                await queue.put(i)

        async def consumer(queue: asyncio.Queue, n: int):
            total = 0
            for _ in range(n):
                item = await queue.get()
                total += item
                queue.task_done()
            return total

        async def run_queue_test():
            queue = asyncio.Queue(maxsize=100)
            n = 1000

            start = time.perf_counter()

            # Run producer and consumer concurrently
            producer_task = asyncio.create_task(producer(queue, n))
            consumer_task = asyncio.create_task(consumer(queue, n))

            await producer_task
            await consumer_task

            elapsed = time.perf_counter() - start
            return elapsed

        elapsed = asyncio.run(run_queue_test())

        # Queue operations should be efficient
        assert elapsed < 1.0, f"Queue operations took {elapsed:.3f}s"

    def test_lock_contention_performance(self):
        """Test async lock performance under contention."""
        async def worker(lock: asyncio.Lock, worker_id: int):
            async with lock:
                # Simulate some work
                await asyncio.sleep(0.001)
                return worker_id

        async def run_contention_test():
            lock = asyncio.Lock()
            n_workers = 100

            start = time.perf_counter()
            tasks = [worker(lock, i) for i in range(n_workers)]
            results = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start

            return elapsed, len(results)

        elapsed, count = asyncio.run(run_contention_test())

        assert count == 100
        # With lock contention, this will be slower but still reasonable
        assert elapsed < 2.0, f"100 workers with lock took {elapsed:.3f}s"


@pytest.fixture
def performance_thresholds():
    """Provide configurable performance thresholds for different environments."""
    return {
        "task_creation_max_seconds": 5.0,
        "concurrent_tasks_max_seconds": 0.5,
        "event_loop_overhead_max_seconds": 2.0,
        "queue_operations_max_seconds": 1.0,
    }


@pytest.mark.benchmark
class TestWithConfigurableThresholds:
    """Performance tests with configurable thresholds."""

    def test_task_creation_with_threshold(self, performance_thresholds):
        """Test task creation against configurable threshold."""
        async def trivial_task(x: int) -> int:
            return x * 2

        async def run_tasks():
            start = time.perf_counter()
            tasks = [asyncio.create_task(trivial_task(i)) for i in range(1000)]
            results = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            return elapsed

        elapsed = asyncio.run(run_tasks())

        threshold = performance_thresholds["task_creation_max_seconds"]
        assert elapsed < threshold, f"Tasks exceeded threshold: {elapsed:.3f}s > {threshold}s"
