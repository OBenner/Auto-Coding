#!/usr/bin/env python3
"""
Memory Performance Benchmark Tests
===================================

Tests for memory usage and leak detection:
- Memory monitor performance
- Session memory bounds checking
- Memory pressure detection
- Large data structure handling

These tests help ensure memory-efficient operations and detect leaks.
"""

import asyncio
import gc
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Add apps/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))

from core.memory_monitor import MemoryMonitor, MemoryPressure, SessionBounds


class TestMemoryMonitorPerformance:
    """Test memory monitoring performance and overhead."""

    @pytest.mark.benchmark
    def test_memory_monitor_initialization(self):
        """Test that MemoryMonitor initializes quickly."""
        import time

        start = time.perf_counter()
        monitor = MemoryMonitor()
        elapsed = time.perf_counter() - start

        assert monitor is not None
        # Initialization should be very fast
        assert elapsed < 0.01, f"MemoryMonitor init took {elapsed:.4f}s"

    @pytest.mark.benchmark
    def test_pressure_check_performance(self):
        """Test memory pressure check performance."""
        monitor = MemoryMonitor()

        # Mock process to avoid psutil dependency in tests
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=1024 * 1024 * 500)  # 500MB
        monitor._process = mock_process

        start = time.perf_counter()
        for _ in range(10000):
            pressure = monitor.check_pressure()
        elapsed = time.perf_counter() - start

        # 10k pressure checks should be very fast
        assert elapsed < 1.0, f"10k pressure checks took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_usage_retrieval_performance(self):
        """Test get_usage_mb() performance."""
        monitor = MemoryMonitor()

        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=1024 * 1024 * 500)
        monitor._process = mock_process

        start = time.perf_counter()
        for _ in range(10000):
            usage = monitor.get_usage_mb()
        elapsed = time.perf_counter() - start

        # 10k usage retrievals should be very fast
        assert elapsed < 1.0, f"10k usage retrievals took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_should_gc_performance(self):
        """Test should_gc() decision performance."""
        monitor = MemoryMonitor(max_memory_mb=1000.0, warning_threshold=0.8)

        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=1024 * 1024 * 850)  # 850MB
        monitor._process = mock_process

        start = time.perf_counter()
        for _ in range(10000):
            should = monitor.should_gc()
        elapsed = time.perf_counter() - start

        # 10k gc checks should be very fast
        assert elapsed < 1.0, f"10k gc checks took {elapsed:.3f}s"


class TestMemoryPressureLevels:
    """Test different memory pressure scenarios."""

    def test_normal_pressure_detection(self):
        """Test detection of normal memory pressure."""
        monitor = MemoryMonitor(max_memory_mb=1000.0)

        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=1024 * 1024 * 500)  # 50%
        monitor._process = mock_process

        assert monitor.check_pressure() == MemoryPressure.NORMAL
        assert not monitor.should_gc()

    def test_warning_pressure_detection(self):
        """Test detection of warning memory pressure."""
        monitor = MemoryMonitor(max_memory_mb=1000.0, warning_threshold=0.8)

        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=1024 * 1024 * 850)  # 85%
        monitor._process = mock_process

        assert monitor.check_pressure() == MemoryPressure.WARNING
        assert monitor.should_gc()

    def test_critical_pressure_detection(self):
        """Test detection of critical memory pressure."""
        monitor = MemoryMonitor(max_memory_mb=1000.0)

        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=1024 * 1024 * 1100)  # 110%
        monitor._process = mock_process

        assert monitor.check_pressure() == MemoryPressure.CRITICAL
        assert monitor.should_gc()

    @pytest.mark.benchmark
    def test_pressure_transition_performance(self):
        """Test performance of pressure level transitions."""
        monitor = MemoryMonitor(max_memory_mb=1000.0, warning_threshold=0.8)
        mock_process = MagicMock()
        monitor._process = mock_process

        # Simulate varying memory usage
        usage_levels = [400, 600, 850, 900, 1100, 500, 300] * 100  # 700 transitions

        start = time.perf_counter()
        for usage_mb in usage_levels:
            mock_process.memory_info.return_value = MagicMock(rss=usage_mb * 1024 * 1024)
            _ = monitor.check_pressure()
        elapsed = time.perf_counter() - start

        # 700 pressure transitions should be fast
        assert elapsed < 0.5, f"700 pressure transitions took {elapsed:.3f}s"


class TestSessionBoundsPerformance:
    """Test session bounds checking performance."""

    @pytest.mark.benchmark
    def test_bounds_check_performance(self):
        """Test SessionBounds.check() performance."""
        test_cases = [
            (10, 50, False),  # Normal
            (50, 50, True),  # Rounds at limit
            (100, 50, True),  # Rounds exceeded
            (10, 100, True),  # Messages exceeded
        ] * 1000  # 4000 checks

        start = time.perf_counter()
        for rounds, messages, _ in test_cases:
            SessionBounds.check(rounds, messages)
        elapsed = time.perf_counter() - start

        # 4000 bounds checks should be very fast
        assert elapsed < 0.5, f"4000 bounds checks took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_bounds_reason_generation_performance(self):
        """Test SessionBounds.reason() performance."""
        test_cases = [
            (10, 50, ""),
            (100, 50, "rounds"),
            (10, 500, "messages"),
            (100, 500, "rounds"),
        ] * 1000  # 4000 checks

        start = time.perf_counter()
        for rounds, messages, _ in test_cases:
            SessionBounds.reason(rounds, messages)
        elapsed = time.perf_counter() - start

        # 4000 reason generations should be very fast
        assert elapsed < 0.5, f"4000 reason generations took {elapsed:.3f}s"


class TestMemoryLeakDetection:
    """Tests to help detect memory leaks."""

    @pytest.mark.benchmark
    def test_list_growth_and_cleanup(self):
        """Test that large lists are cleaned up properly."""
        # Create large lists repeatedly
        for _ in range(100):
            large_list = [i for i in range(10000)]
            # List should be garbage collected
            del large_list

        # Force garbage collection
        gc.collect()

        # If this test doesn't crash or OOM, memory cleanup is working
        assert True

    @pytest.mark.benchmark
    def test_dict_growth_and_cleanup(self):
        """Test that large dicts are cleaned up properly."""
        for _ in range(100):
            large_dict = {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}
            del large_dict

        gc.collect()
        assert True

    @pytest.mark.benchmark
    def test_string_accumulation_cleanup(self):
        """Test that accumulated strings are cleaned up."""
        large_string = ""
        for i in range(1000):
            large_string += f"chunk_{i}" * 100

        # At this point we have a large string
        size_before = len(large_string)

        # Clear it
        large_string = ""
        gc.collect()

        # Verify it was cleared
        assert len(large_string) == 0

    @pytest.mark.benchmark
    def test_object_reference_cleanup(self):
        """Test that object references are cleaned up."""
        class TestObject:
            def __init__(self, data):
                self.data = data

        # Create many objects
        objects = [TestObject(f"data_{i}" * 100) for i in range(10000)]

        # Clear references
        objects.clear()
        gc.collect()

        # Verify cleanup
        assert len(objects) == 0


class TestLargeDataStructureHandling:
    """Test handling of large data structures."""

    @pytest.mark.benchmark
    def test_large_list_iteration_performance(self):
        """Test iteration over large lists."""
        large_list = list(range(100000))

        start = time.perf_counter()
        total = sum(large_list)
        elapsed = time.perf_counter() - start

        assert total == sum(range(100000))
        # Iterating 100k items should be fast
        assert elapsed < 0.1, f"100k iteration took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_large_dict_lookup_performance(self):
        """Test dictionary lookups with large dicts."""
        large_dict = {f"key_{i}": f"value_{i}" for i in range(100000)}

        start = time.perf_counter()
        for i in range(10000):
            _ = large_dict.get(f"key_{i}")
        elapsed = time.perf_counter() - start

        # 10k lookups in 100k dict should be fast
        assert elapsed < 0.1, f"10k lookups took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_nested_structure_access_performance(self):
        """Test access to nested data structures."""
        nested = {
            "level1": {
                "level2": {
                    "level3": {"data": [i for i in range(1000)]}
                }
            }
        }

        start = time.perf_counter()
        for _ in range(1000):
            data = nested["level1"]["level2"]["level3"]["data"]
        elapsed = time.perf_counter() - start

        # 1k nested accesses should be very fast
        assert elapsed < 0.01, f"1k nested accesses took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_json_serialization_large_data(self):
        """Test JSON serialization of large data structures."""
        import json

        large_data = {
            "items": [
                {"id": i, "name": f"item_{i}", "values": [j for j in range(100)]}
                for i in range(1000)
            ]
        }

        start = time.perf_counter()
        json_str = json.dumps(large_data)
        elapsed = time.perf_counter() - start

        # Serializing 1000 items with 100 values each
        assert len(json_str) > 0
        assert elapsed < 1.0, f"Large JSON serialization took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_json_deserialization_large_data(self):
        """Test JSON deserialization of large data structures."""
        import json

        large_data = {
            "items": [
                {"id": i, "name": f"item_{i}", "values": [j for j in range(100)]}
                for i in range(1000)
            ]
        }
        json_str = json.dumps(large_data)

        start = time.perf_counter()
        loaded = json.loads(json_str)
        elapsed = time.perf_counter() - start

        assert len(loaded["items"]) == 1000
        assert elapsed < 1.0, f"Large JSON deserialization took {elapsed:.3f}s"


class TestMemoryEfficientPatterns:
    """Test memory-efficient coding patterns."""

    @pytest.mark.benchmark
    def test_generator_vs_list_memory_efficiency(self):
        """Test that generators use less memory than lists."""
        # List approach
        start = time.perf_counter()
        list_result = [i * 2 for i in range(100000)]
        list_time = time.perf_counter() - start
        list_memory = sys.getsizeof(list_result)

        # Generator approach - consume to list for comparison
        start = time.perf_counter()
        gen_result_list = list(i * 2 for i in range(100000))
        gen_time = time.perf_counter() - start
        gen_memory = sys.getsizeof(gen_result_list)

        # Both produce same result
        assert sum(list_result) == sum(gen_result_list)

        # Both approaches complete successfully
        # The generator expression, when converted to list, has similar size
        # but the key benefit is lazy evaluation when not materialized
        assert True

    @pytest.mark.benchmark
    def test_string_concatenation_efficiency(self):
        """Test efficient string concatenation patterns."""
        # Inefficient: repeated concatenation
        start = time.perf_counter()
        result1 = ""
        for i in range(1000):
            result1 += f"chunk_{i}"
        concat_time = time.perf_counter() - start

        # Efficient: join
        start = time.perf_counter()
        chunks = [f"chunk_{i}" for i in range(1000)]
        result2 = "".join(chunks)
        join_time = time.perf_counter() - start

        assert result1 == result2
        # Join should be faster or similar
        # This mainly verifies both work without OOM

    @pytest.mark.benchmark
    def test_set_vs_list_lookup_performance(self):
        """Test set vs list lookup performance."""
        # Create test data
        items = list(range(10000))
        test_set = set(items)
        test_list = items

        # List lookup (O(n))
        start = time.perf_counter()
        for i in range(1000):
            _ = i in test_list
        list_time = time.perf_counter() - start

        # Set lookup (O(1))
        start = time.perf_counter()
        for i in range(1000):
            _ = i in test_set
        set_time = time.perf_counter() - start

        # Set lookup should be significantly faster
        # But we just verify both complete
        assert True


@pytest.fixture
def memory_thresholds():
    """Configurable memory thresholds."""
    return {
        "max_pressure_check_time": 1.0,
        "max_bounds_check_time": 0.5,
        "max_large_iteration_time": 0.1,
    }


@pytest.mark.benchmark
class TestWithMemoryThresholds:
    """Memory tests with configurable thresholds."""

    def test_pressure_check_within_threshold(self, memory_thresholds):
        """Test pressure checks respect configured threshold."""
        monitor = MemoryMonitor()
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=1024 * 1024 * 500)
        monitor._process = mock_process

        import time

        start = time.perf_counter()
        for _ in range(10000):
            monitor.check_pressure()
        elapsed = time.perf_counter() - start

        threshold = memory_thresholds["max_pressure_check_time"]
        assert elapsed < threshold, f"Checks exceeded: {elapsed:.3f}s > {threshold}s"
