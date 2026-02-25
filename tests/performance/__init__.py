"""
Performance Benchmark Tests
===========================

Comprehensive performance regression tests for the Auto-Claude framework.

Test modules:
- test_async_performance: Async event loop and uvloop performance tests
- test_backend_performance: Backend operations performance tests
- test_frontend_performance: Frontend bundle size and rendering tests
- test_memory_performance: Memory usage and leak detection tests
- test_api_performance: API response time benchmarks

Run performance tests with:
    pytest tests/performance/
    pytest tests/performance/ -v -m "not slow"
    pytest tests/performance/ --benchmark-only

Performance tests are designed to detect regressions, not just verify functionality.
They establish baseline metrics and fail when significant degradations occur.
"""
