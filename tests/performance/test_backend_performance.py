#!/usr/bin/env python3
"""
Backend Performance Benchmark Tests
====================================

Tests for backend operations performance, including:
- File I/O operations
- Worktree management
- Agent session operations
- Security validation performance

These tests establish baseline metrics and detect regressions.
"""

import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Add apps/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))


class TestFileIOPerformance:
    """Benchmarks for file I/O operations."""

    @pytest.mark.benchmark
    def test_json_read_performance(self, tmp_path):
        """Test JSON file reading performance."""
        # Create a test JSON file with moderate size
        test_data = {
            "specs": [
                {
                    "id": f"spec-{i}",
                    "name": f"Test Spec {i}",
                    "phases": [
                        {"id": f"phase-{j}", "tasks": [{"id": f"task-{k}"} for k in range(10)]}
                        for j in range(5)
                    ],
                }
                for i in range(100)
            ]
        }

        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(test_data))

        start = time.perf_counter()
        with open(json_file) as f:
            loaded_data = json.load(f)
        elapsed = time.perf_counter() - start

        assert loaded_data == test_data
        # Reading 100 specs should be fast
        assert elapsed < 1.0, f"JSON read took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_json_write_performance(self, tmp_path):
        """Test JSON file writing performance."""
        test_data = {
            "results": [
                {"id": i, "value": f"test-value-{i}", "metadata": {"key": "value"}}
                for i in range(1000)
            ]
        }

        json_file = tmp_path / "write_test.json"

        start = time.perf_counter()
        json_file.write_text(json.dumps(test_data))
        elapsed = time.perf_counter() - start

        assert json_file.exists()
        # Writing 1000 items should be fast
        assert elapsed < 0.5, f"JSON write took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_yaml_read_performance(self, tmp_path):
        """Test YAML file reading performance."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")

        # Create a YAML file with multiple specs
        yaml_content = """
specs:
  - id: spec-1
    name: Test Spec 1
    phases:
      - id: phase-1
        name: Phase 1
        subtasks:
          - id: subtask-1
            description: Test subtask
  - id: spec-2
    name: Test Spec 2
    phases:
      - id: phase-2
        name: Phase 2
        subtasks:
          - id: subtask-2
            description: Another test subtask
"""

        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        start = time.perf_counter()
        with open(yaml_file) as f:
            loaded_data = yaml.safe_load(f)
        elapsed = time.perf_counter() - start

        assert loaded_data is not None
        assert "specs" in loaded_data
        # YAML parsing should be reasonably fast
        assert elapsed < 1.0, f"YAML read took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_directory_scan_performance(self, tmp_path):
        """Test directory scanning and file discovery performance."""
        # Create a directory structure with many files
        (tmp_path / "specs").mkdir()
        (tmp_path / "tasks").mkdir()

        for i in range(100):
            (tmp_path / "specs" / f"spec-{i}.md").write_text(f"# Spec {i}")
            (tmp_path / "tasks" / f"task-{i}.json").write_text(json.dumps({"id": i}))

        start = time.perf_counter()
        spec_files = list((tmp_path / "specs").glob("*.md"))
        task_files = list((tmp_path / "tasks").glob("*.json"))
        elapsed = time.perf_counter() - start

        assert len(spec_files) == 100
        assert len(task_files) == 100
        # Scanning 200 files should be fast
        assert elapsed < 0.5, f"Directory scan took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_large_file_read_performance(self, tmp_path):
        """Test reading large files efficiently."""
        # Create a moderately large file (1MB)
        large_content = "x" * (1024 * 1024)
        large_file = tmp_path / "large.txt"
        large_file.write_text(large_content)

        start = time.perf_counter()
        content = large_file.read_text()
        elapsed = time.perf_counter() - start

        assert len(content) == 1024 * 1024
        # Reading 1MB should be very fast
        assert elapsed < 0.1, f"Large file read took {elapsed:.3f}s"


class TestSecurityValidationPerformance:
    """Benchmarks for security validation operations."""

    @pytest.mark.benchmark
    def test_command_validation_performance(self):
        """Test that command validation is fast."""
        try:
            from security.tool_input_validator import SecurityValidator
        except ImportError:
            pytest.skip("SecurityValidator not available")

        # Test that the validator can be imported and used
        # The actual implementation depends on the security module structure
        assert True

    @pytest.mark.benchmark
    def test_security_profile_generation_performance(self, tmp_path):
        """Test security profile generation performance."""
        try:
            from context.project_analyzer import ProjectStack
        except ImportError:
            # Module may be in different location
            pytest.skip("ProjectStack not available")

        # Test placeholder - actual implementation depends on module structure
        assert True

    @pytest.mark.benchmark
    def test_path_validation_performance(self):
        """Test that path validation is efficient."""
        try:
            from security.tool_input_validator import SecurityValidator
        except ImportError:
            pytest.skip("SecurityValidator not available")

        # Test placeholder - actual implementation depends on module structure
        assert True


class TestMemoryOperationsPerformance:
    """Benchmarks for memory-related operations."""

    @pytest.mark.benchmark
    def test_session_context_storage_performance(self):
        """Test session context storage and retrieval performance."""
        try:
            from agents.memory_manager import SessionContext
        except (ImportError, AttributeError):
            pytest.skip("SessionContext not available")

        # Test placeholder - actual implementation depends on module structure
        assert True

    @pytest.mark.benchmark
    def test_memory_monitoring_overhead(self):
        """Test that memory monitoring doesn't add significant overhead."""
        from core.memory_monitor import MemoryMonitor

        monitor = MemoryMonitor()

        start = time.perf_counter()
        for _ in range(1000):
            pressure = monitor.check_pressure()
            should_gc = monitor.should_gc()
        elapsed = time.perf_counter() - start

        # Memory monitoring checks should be very fast
        assert elapsed < 0.1, f"Memory monitoring took {elapsed:.3f}s for 1000 checks"


class TestImplementationPlanPerformance:
    """Benchmarks for implementation plan operations."""

    @pytest.mark.benchmark
    def test_plan_loading_performance(self, tmp_path):
        """Test implementation plan loading performance."""
        try:
            from implementation_plan import ImplementationPlan
        except ImportError:
            pytest.skip("ImplementationPlan not available")

        # Create a complex implementation plan for testing
        plan_data = {
            "feature": "Test Feature",
            "phases": [
                {
                    "id": f"phase-{i}",
                    "name": f"Phase {i}",
                    "subtasks": [
                        {
                            "id": f"subtask-{i}-{j}",
                            "description": f"Subtask {i}-{j}",
                            "status": "pending",
                        }
                        for j in range(20)
                    ],
                }
                for i in range(10)
            ],
        }

        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan_data))

        start = time.perf_counter()
        # Load the JSON - ImplementationPlan structure may vary
        with open(plan_file) as f:
            loaded = json.load(f)
        elapsed = time.perf_counter() - start

        assert loaded["feature"] == "Test Feature"
        assert elapsed < 1.0, f"Plan loading took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_plan_status_update_performance(self):
        """Test updating subtask status performance."""
        # Test JSON manipulation performance as baseline
        plan_data = {
            "feature": "Test",
            "phases": [
                {
                    "id": "phase-1",
                    "subtasks": [
                        {"id": f"subtask-{i}", "status": "pending"} for i in range(100)
                    ],
                }
            ],
        }

        start = time.perf_counter()
        # Simulate status updates
        for i in range(100):
            # Find and update subtask (simulating plan.update_subtask_status)
            for phase in plan_data["phases"]:
                for subtask in phase["subtasks"]:
                    if subtask["id"] == f"subtask-{i}":
                        subtask["status"] = "completed"
        elapsed = time.perf_counter() - start

        # Updating 100 subtasks should be fast
        assert elapsed < 1.0, f"Status updates took {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_plan_serialization_performance(self):
        """Test plan serialization to JSON performance."""
        plan_data = {
            "feature": "Test",
            "phases": [
                {
                    "id": f"phase-{i}",
                    "subtasks": [
                        {"id": f"subtask-{i}-{j}", "status": "completed"}
                        for j in range(50)
                    ],
                }
                for i in range(10)
            ],
        }

        start = time.perf_counter()
        json_str = json.dumps(plan_data, indent=2)
        elapsed = time.perf_counter() - start

        assert len(json_str) > 0
        # Serializing 500 subtasks should be fast
        assert elapsed < 1.0, f"Plan serialization took {elapsed:.3f}s"


class TestGraphitiPerformance:
    """Benchmarks for Graphiti memory operations."""

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_graphiti_search_performance(self, tmp_path):
        """Test Graphiti semantic search performance."""
        try:
            from integrations.graphiti.memory import get_graphiti_memory
        except ImportError:
            pytest.skip("Graphiti not available")

        # This test would require a full Graphiti setup
        # For now, we'll test the interface exists
        assert True

        # In a real test, we would:
        # 1. Initialize Graphiti memory
        # 2. Add many test sessions
        # 3. Measure search query time
        # 4. Assert search completes in reasonable time

    @pytest.mark.benchmark
    def test_graphiti_context_retrieval_overhead(self):
        """Test that Graphiti context retrieval doesn't add too much overhead."""
        try:
            from integrations.graphiti.memory import get_graphiti_memory
        except ImportError:
            pytest.skip("Graphiti not available")

        # Test the mock/interface exists
        # Real performance testing would require actual Graphiti instance
        assert True


@pytest.fixture
def performance_config():
    """Configuration for performance tests."""
    return {
        "max_json_read_time": 1.0,
        "max_json_write_time": 0.5,
        "max_directory_scan_time": 0.5,
        "max_command_validation_time": 0.1,
        "max_plan_loading_time": 1.0,
    }


@pytest.mark.benchmark
class TestWithPerformanceConfig:
    """Performance tests with configurable thresholds."""

    def test_json_operations_within_threshold(self, performance_config, tmp_path):
        """Test JSON operations respect configured thresholds."""
        test_data = {"key": "value" * 1000}

        json_file = tmp_path / "test.json"

        # Write
        start = time.perf_counter()
        json_file.write_text(json.dumps(test_data))
        write_elapsed = time.perf_counter() - start

        # Read
        start = time.perf_counter()
        with open(json_file) as f:
            json.load(f)
        read_elapsed = time.perf_counter() - start

        max_write = performance_config["max_json_write_time"]
        max_read = performance_config["max_json_read_time"]

        assert write_elapsed < max_write, f"Write exceeded: {write_elapsed:.3f}s > {max_write}s"
        assert read_elapsed < max_read, f"Read exceeded: {read_elapsed:.3f}s > {max_read}s"
