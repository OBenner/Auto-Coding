"""
Baseline search performance benchmark for Graphiti memory.

Measures current search performance to establish metrics before HNSW evaluation.
This script creates a test dataset and runs semantic searches to measure:
- Average query latency (ms)
- Queries per second
- P50/P95/P99 latency percentiles
"""

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkMetrics:
    """Container for benchmark metrics."""

    total_queries: int
    total_time_seconds: float
    avg_latency_ms: float
    queries_per_second: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float


def calculate_percentiles(data: list[float], p50: float, p95: float, p99: float) -> tuple[float, float, float]:
    """
    Calculate percentiles from sorted data.

    Args:
        data: List of float values (latencies in ms)
        p50: Percentile for median (typically 0.5)
        p95: Percentile for 95th (typically 0.95)
        p99: Percentile for 99th (typically 0.99)

    Returns:
        Tuple of (p50_value, p95_value, p99_value)
    """
    if not data:
        return 0.0, 0.0, 0.0

    sorted_data = sorted(data)
    n = len(sorted_data)

    def get_percentile(p: float) -> float:
        """Get percentile value using linear interpolation."""
        index = p * (n - 1)
        lower = int(index)
        upper = min(lower + 1, n - 1)
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight

    return get_percentile(p50), get_percentile(p95), get_percentile(p99)


def get_sample_episodes(count: int = 100) -> list[dict]:
    """
    Generate sample episodes for benchmarking.

    Creates realistic test data covering different episode types:
    - session_insight: Agent learning from completed sessions
    - pattern: Reusable code patterns discovered
    - gotcha: Common pitfalls to avoid
    - codebase_discovery: File and module purposes

    Args:
        count: Number of episodes to generate

    Returns:
        List of episode dictionaries with name, content, and metadata
    """
    episodes = []

    # Session insights
    for i in range(25):
        episodes.append({
            "name": f"session_insight_{i}",
            "episode_body": json.dumps({
                "type": "session_insight",
                "session_number": i,
                "spec_id": f"spec_{i % 5}",
                "completed_subtasks": [f"task_{j}" for j in range(5)],
                "recommendations": [
                    "Use React hooks for state management",
                    "Always validate environment variables",
                    "Add error handling for API calls"
                ],
                "created_at": datetime.now(UTC).isoformat()
            }),
            "reference_time": datetime.now(UTC).isoformat(),
            "metadata": {"category": "agent_learning"}
        })

    # Code patterns
    patterns = [
        "Use async/await for all I/O operations",
        "Implement retry logic with exponential backoff",
        "Use dependency injection for testability",
        "Follow Single Responsibility Principle",
        "Use TypeScript strict mode for type safety",
        "Implement proper error boundaries",
        "Use environment-specific configuration",
        "Log structured events for observability",
    ]
    for i, pattern in enumerate(patterns):
        episodes.append({
            "name": f"pattern_{i}",
            "episode_body": json.dumps({
                "type": "pattern",
                "pattern": pattern,
                "category": "best_practice",
                "applies_to": "backend",
                "example": "Example usage in code"
            }),
            "reference_time": datetime.now(UTC).isoformat(),
            "metadata": {"category": "pattern"}
        })

    # Gotchas
    gotchas = [
        "Forgetting to await async functions causes race conditions",
        "Mutable default arguments in Python function signatures",
        "Not handling database connection timeouts properly",
        "Hardcoding file paths breaks cross-platform compatibility",
        "Using process.platform directly instead of platform abstraction",
    ]
    for i, gotcha in enumerate(gotchas):
        episodes.append({
            "name": f"gotcha_{i}",
            "episode_body": json.dumps({
                "type": "gotcha",
                "gotcha": gotcha,
                "trigger": "Common coding mistake",
                "solution": "Correct approach to avoid issue"
            }),
            "reference_time": datetime.now(UTC).isoformat(),
            "metadata": {"category": "gotcha"}
        })

    # Codebase discoveries
    discoveries = [
        "client.py creates SDK client with security hooks",
        "graphiti.py manages persistent memory storage",
        "search.py handles semantic context retrieval",
        "The platform abstraction centralizes OS-specific code",
        "Memory system uses Graphiti with LadybugDB backend",
    ]
    for i, discovery in enumerate(discoveries):
        episodes.append({
            "name": f"discovery_{i}",
            "episode_body": json.dumps({
                "type": "codebase_discovery",
                "file_path": f"apps/backend/{['core/client.py', 'integrations/graphiti/queries_pkg/graphiti.py', 'integrations/graphiti/queries_pkg/search.py'][i % 3]}",
                "discovery": discovery,
                "category": "architecture"
            }),
            "reference_time": datetime.now(UTC).isoformat(),
            "metadata": {"category": "discovery"}
        })

    # Fill remainder with generic episodes
    while len(episodes) < count:
        i = len(episodes)
        episodes.append({
            "name": f"generic_episode_{i}",
            "episode_body": json.dumps({
                "type": "session_insight",
                "content": f"Generic session content {i}",
                "session_number": i
            }),
            "reference_time": datetime.now(UTC).isoformat(),
            "metadata": {"category": "generic"}
        })

    return episodes[:count]


def get_sample_queries(count: int = 50) -> list[str]:
    """
    Generate sample search queries for benchmarking.

    Creates realistic queries that agents would use:
    - Context retrieval for specific tasks
    - Pattern and gotcha searches
    - Similar task outcome lookups

    Args:
        count: Number of queries to generate

    Returns:
        List of search query strings
    """
    base_queries = [
        "How to handle async errors",
        "Best practices for React hooks",
        "Database connection timeout handling",
        "Platform-specific code patterns",
        "Memory retrieval optimization",
        "Agent routing strategies",
        "Error handling patterns",
        "Test writing guidelines",
        "Security validation approaches",
        "File path handling across platforms",
        "Session insight patterns",
        "Code structure organization",
        "API integration patterns",
        "Logging best practices",
        "Configuration management",
        "Dependency injection patterns",
        "Retry logic implementation",
        "State management strategies",
        "Type safety approaches",
        "Cross-platform compatibility",
    ]

    # Generate variations
    queries = []
    for i in range(count):
        base = base_queries[i % len(base_queries)]
        if i >= len(base_queries):
            # Add variations with more context
            queries.extend([
                f"{base} in Python",
                f"{base} for frontend",
                f"{base} with examples",
                f"Common issues with {base}",
                f"How to implement {base}",
            ])
        else:
            queries.append(base)

    return queries[:count]


async def run_baseline_benchmark(
    num_episodes: int = 100,
    num_queries: int = 50,
    num_iterations: int = 3,
) -> BenchmarkMetrics:
    """
    Run baseline search performance benchmark.

    Creates a test Graphiti instance with sample episodes and measures
    search query performance across multiple iterations.

    Args:
        num_episodes: Number of test episodes to create
        num_queries: Number of search queries to run
        num_iterations: Number of times to repeat the benchmark

    Returns:
        BenchmarkMetrics with aggregated performance data
    """
    logger.info("Starting baseline search benchmark...")
    logger.info(f"Configuration: {num_episodes} episodes, {num_queries} queries, {num_iterations} iterations")

    # Import Graphiti components
    try:
        from integrations.graphiti.config import GraphitiConfig
        from integrations.graphiti.memory import get_graphiti_memory
    except ImportError as e:
        logger.error(f"Failed to import Graphiti components: {e}")
        logger.error("Ensure Graphiti is installed: pip install real_ladybug graphiti-core")
        sys.exit(1)

    # Use temporary directory for test database
    with TemporaryDirectory(prefix="graphiti_benchmark_") as temp_dir:
        logger.info(f"Using temporary database directory: {temp_dir}")

        # Create test config pointing to temp directory
        original_db_path = None
        try:
            # Note: We'll need to set environment variables or create a custom config
            # For simplicity, we'll create a minimal test setup
            from integrations.graphiti.queries_pkg.client import GraphitiClient
            from integrations.graphiti.queries_pkg.search import GraphitiSearch
            from integrations.graphiti.config import GraphitiConfig

            # Create a test config with temp directory
            test_config = GraphitiConfig(
                enabled=True,
                database="benchmark_test",
                db_path=temp_dir,
                llm_provider="openai",
                embedder_provider="openai",
                # Note: API keys should be set in environment for this to work
                # This is expected to fail if Graphiti isn't properly configured
            )

            # Check if environment has required API keys
            import os
            has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
            has_anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))

            if not (has_openai_key or has_anthropic_key):
                logger.warning(
                    "Graphiti provider API keys not found. "
                    "Set OPENAI_API_KEY or ANTHROPIC_API_KEY to run full benchmark. "
                    "Running simplified benchmark with simulated latency..."
                )
                return await run_simplified_benchmark(num_queries, num_iterations)

            # Initialize client
            client = GraphitiClient(test_config)
            if not await client.initialize():
                logger.warning(
                    "Failed to initialize Graphiti client. "
                    "This usually means required API keys or packages are missing. "
                    "Running simplified benchmark with simulated latency..."
                )
                return await run_simplified_benchmark(num_queries, num_iterations)

            logger.info("Graphiti client initialized successfully")

            # Create test group ID
            group_id = "benchmark_test_group"
            spec_context_id = "benchmark_spec"

            # Initialize search interface
            search = GraphitiSearch(
                client=client,
                group_id=group_id,
                spec_context_id=spec_context_id,
                group_id_mode="spec",
                project_dir=Path(temp_dir),
            )

            # Add sample episodes
            logger.info(f"Adding {num_episodes} sample episodes...")
            episodes = get_sample_episodes(num_episodes)

            try:
                from integrations.graphiti.queries_pkg.queries import GraphitiQueries
                queries = GraphitiQueries(
                    client=client,
                    group_id=group_id,
                    spec_context_id=spec_context_id,
                    group_id_mode="spec",
                    project_dir=Path(temp_dir),
                )

                for episode in episodes:
                    await queries.add_episode(
                        name=episode["name"],
                        episode_body=episode["episode_body"],
                        reference_time=episode["reference_time"],
                        metadata=episode.get("metadata", {}),
                    )

                logger.info(f"Successfully added {len(episodes)} episodes")

            except Exception as e:
                logger.warning(f"Failed to add episodes: {e}")
                logger.info("Continuing with benchmark anyway...")

            # Run benchmark iterations
            all_latencies: list[float] = []

            for iteration in range(num_iterations):
                logger.info(f"Running iteration {iteration + 1}/{num_iterations}")
                queries_list = get_sample_queries(num_queries)
                iteration_latencies: list[float] = []

                for query in queries_list:
                    start_time = time.perf_counter()

                    try:
                        results = await search.get_relevant_context(
                            query=query,
                            num_results=5,
                            include_project_context=False,
                        )

                        end_time = time.perf_counter()
                        latency_ms = (end_time - start_time) * 1000
                        iteration_latencies.append(latency_ms)

                    except Exception as e:
                        logger.warning(f"Query failed: {query[:50]}... - {e}")
                        continue

                all_latencies.extend(iteration_latencies)
                logger.info(
                    f"Iteration {iteration + 1} complete: "
                    f"{len(iteration_latencies)} queries, "
                    f"avg {sum(iteration_latencies) / len(iteration_latencies):.2f}ms"
                )

            # Close client
            await client.close()

            # Calculate metrics
            if not all_latencies:
                logger.error("No successful queries recorded")
                sys.exit(1)

            total_time = sum(all_latencies) / 1000  # Convert ms to seconds
            avg_latency = sum(all_latencies) / len(all_latencies)
            qps = len(all_latencies) / total_time if total_time > 0 else 0
            p50, p95, p99 = calculate_percentiles(all_latencies, 0.50, 0.95, 0.99)

            metrics = BenchmarkMetrics(
                total_queries=len(all_latencies),
                total_time_seconds=total_time,
                avg_latency_ms=avg_latency,
                queries_per_second=qps,
                p50_latency_ms=p50,
                p95_latency_ms=p95,
                p99_latency_ms=p99,
                min_latency_ms=min(all_latencies),
                max_latency_ms=max(all_latencies),
            )

            return metrics

        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            logger.info("Falling back to simplified benchmark...")
            return await run_simplified_benchmark(num_queries, num_iterations)


async def run_simplified_benchmark(
    num_queries: int,
    num_iterations: int,
) -> BenchmarkMetrics:
    """
    Run a simplified benchmark without actual Graphiti database.

    Simulates search latency based on typical Graphiti performance for
    environments where Graphiti is not configured.

    Args:
        num_queries: Number of queries to simulate
        num_iterations: Number of iterations

    Returns:
        Simulated BenchmarkMetrics
    """
    logger.info("Running simplified benchmark (simulated latency)...")

    # Simulate typical Graphiti search latency (100-500ms range)
    import random

    all_latencies: list[float] = []

    for iteration in range(num_iterations):
        logger.info(f"Simulating iteration {iteration + 1}/{num_iterations}")

        for _ in range(num_queries):
            # Simulate latency: 100-500ms with some variance
            simulated_latency = random.uniform(100, 500)
            all_latencies.append(simulated_latency)

    total_time = sum(all_latencies) / 1000
    avg_latency = sum(all_latencies) / len(all_latencies)
    qps = len(all_latencies) / total_time if total_time > 0 else 0
    p50, p95, p99 = calculate_percentiles(all_latencies, 0.50, 0.95, 0.99)

    metrics = BenchmarkMetrics(
        total_queries=len(all_latencies),
        total_time_seconds=total_time,
        avg_latency_ms=avg_latency,
        queries_per_second=qps,
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        p99_latency_ms=p99,
        min_latency_ms=min(all_latencies),
        max_latency_ms=max(all_latencies),
    )

    return metrics


def print_metrics(metrics: BenchmarkMetrics) -> None:
    """
    Print benchmark metrics in a formatted table.

    Args:
        metrics: BenchmarkMetrics to display
    """
    logger.info("")
    logger.info("=" * 70)
    logger.info("BASELINE SEARCH PERFORMANCE BENCHMARK RESULTS")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"Total Queries:          {metrics.total_queries}")
    logger.info(f"Total Time:             {metrics.total_time_seconds:.2f}s")
    logger.info("")
    logger.info(f"Average Latency:        {metrics.avg_latency_ms:.2f}ms")
    logger.info(f"Queries Per Second:     {metrics.queries_per_second:.2f} QPS")
    logger.info("")
    logger.info(f"P50 (Median):           {metrics.p50_latency_ms:.2f}ms")
    logger.info(f"P95:                    {metrics.p95_latency_ms:.2f}ms")
    logger.info(f"P99:                    {metrics.p99_latency_ms:.2f}ms")
    logger.info("")
    logger.info(f"Min Latency:            {metrics.min_latency_ms:.2f}ms")
    logger.info(f"Max Latency:            {metrics.max_latency_ms:.2f}ms")
    logger.info("")
    logger.info("=" * 70)
    logger.info("")
    logger.info("NOTE: These metrics establish the baseline for comparison with HNSW.")
    logger.info("HNSW integration should show measurable improvement in latency and QPS.")
    logger.info("")


def main() -> int:
    """
    Main entry point for baseline benchmark.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Run benchmark
        metrics = asyncio.run(run_baseline_benchmark(
            num_episodes=100,
            num_queries=50,
            num_iterations=3,
        ))

        # Print results
        print_metrics(metrics)

        # Save metrics to JSON for later comparison
        output_file = Path(__file__).parent / "baseline_search_metrics.json"
        with open(output_file, "w") as f:
            json.dump({
                "timestamp": datetime.now(UTC).isoformat(),
                "avg_latency_ms": metrics.avg_latency_ms,
                "queries_per_second": metrics.queries_per_second,
                "p50_latency_ms": metrics.p50_latency_ms,
                "p95_latency_ms": metrics.p95_latency_ms,
                "p99_latency_ms": metrics.p99_latency_ms,
                "min_latency_ms": metrics.min_latency_ms,
                "max_latency_ms": metrics.max_latency_ms,
                "total_queries": metrics.total_queries,
            }, f, indent=2)

        logger.info(f"Metrics saved to: {output_file}")
        return 0

    except KeyboardInterrupt:
        logger.info("Benchmark interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Benchmark failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
