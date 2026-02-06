# Analytics Service

## Overview

The Analytics Service provides comprehensive tracking and analysis of agent performance across all Auto Claude tasks. It aggregates metrics from multiple data sources to provide insights into success rates, completion times, error patterns, and quality trends.

## Architecture

### Data Sources

The analytics service aggregates data from:

1. **Cost Reports** (`cost_report.json`) - Token usage and API costs per task
2. **Attempt History** (`attempt_history.json`) - Task execution attempts and outcomes
3. **Implementation Plans** (`implementation_plan.json`) - Task metadata and QA statistics
4. **QA Reports** (`qa_report.md`) - Quality assurance findings and common issues

### Core Components

```
analytics.py (19KB)
├── AnalyticsService - Main service class for data aggregation
├── MetricsSummary - Overall performance metrics
├── AgentStats - Per-agent-type statistics
├── TaskComplexityStats - Performance by task complexity
├── QAStats - Quality assurance metrics
└── TrendDataPoint - Time-series performance data
```

## Data Models

### MetricsSummary
Overall performance metrics across all tasks:
- **total_specs**: Total number of task specs processed
- **successful_specs**: Number of successfully completed specs
- **overall_success_rate**: Percentage of successful completions
- **total_cost**: Cumulative API costs (USD)
- **total_tokens**: Total tokens consumed across all tasks
- **avg_completion_time**: Average task completion time (seconds)
- **total_qa_iterations**: Total QA validation cycles
- **avg_qa_iterations**: Average QA cycles per task

### AgentStats
Performance metrics for each agent type (Planner, Coder, QA):
- **agent_type**: Agent identifier (e.g., "planner_agent", "coder_agent")
- **total_attempts**: Number of times agent was invoked
- **successful_attempts**: Number of successful executions
- **failed_attempts**: Number of failed executions
- **total_cost**: Agent-specific API costs
- **total_tokens**: Agent-specific token usage
- **avg_completion_time**: Average execution time
- **error_patterns**: Dictionary of error types and frequencies

### TaskComplexityStats
Performance breakdown by task complexity:
- **complexity**: Task complexity level (simple, standard, complex)
- **count**: Number of tasks at this complexity
- **success_rate**: Completion success rate
- **avg_completion_time**: Average time to complete
- **avg_cost**: Average API cost per task

### QAStats
Quality assurance metrics:
- **total_qa_sessions**: Total QA validation sessions
- **rejection_rate**: Percentage of tasks initially rejected
- **avg_iterations_to_approval**: Average QA cycles before approval
- **common_issues**: List of most frequent QA findings

### TrendDataPoint
Time-series performance data:
- **date**: ISO date string
- **success_rate**: Success rate on this date
- **total_specs**: Number of specs completed
- **avg_cost**: Average cost per spec
- **avg_tokens**: Average tokens per spec

## Usage

### Python Backend

```python
from apps.backend.services.analytics import AnalyticsService
from pathlib import Path

# Initialize service
service = AnalyticsService(specs_dir=Path(".auto-claude/specs"))

# Get overall metrics
summary = service.get_metrics_summary()
print(f"Success rate: {summary.overall_success_rate:.1f}%")
print(f"Total cost: ${summary.total_cost:.2f}")

# Get per-agent statistics
agent_stats = service.get_agent_stats()
for stats in agent_stats:
    print(f"{stats.agent_type}: {stats.successful_attempts}/{stats.total_attempts} successful")

# Get trend data (last 30 days)
trends = service.get_trend_data(days=30)
for point in trends:
    print(f"{point.date}: {point.success_rate:.1f}% success")

# Get QA metrics
qa_stats = service.get_qa_stats()
print(f"QA rejection rate: {qa_stats.rejection_rate:.1f}%")

# Get complexity breakdown
complexity_stats = service.get_complexity_stats()
for stats in complexity_stats:
    print(f"{stats.complexity}: {stats.success_rate:.1f}% success rate")
```

### CLI Access

The analytics service is exposed via `analytics_cli.py`:

```bash
cd apps/backend
python cli/analytics_cli.py
```

Returns JSON output with all analytics data:
```json
{
  "summary": {
    "total_specs": 42,
    "successful_specs": 38,
    "overall_success_rate": 90.5,
    "total_cost": 12.34,
    "total_tokens": 456789
  },
  "agent_stats": [...],
  "trends": [...],
  "qa_stats": {...},
  "complexity_stats": [...]
}
```

### Frontend Integration

Analytics data flows from backend to UI:

1. **IPC Handlers** (`analytics-handlers.ts`) - Spawn Python CLI and parse JSON
2. **Preload API** (`analytics-api.ts`) - Expose IPC channels to renderer
3. **Frontend Component** (`Analytics.tsx`) - Display charts and metrics

## Features

### Dashboard Views

#### Overview View
- Overall success/failure rate
- Total cost and token usage
- Average completion time
- QA iteration statistics

#### Agents View
- Per-agent performance breakdown
- Success rates by agent type
- Cost and token distribution
- Error pattern analysis

#### Trends View
- Historical performance over time (7, 30, 90 days)
- Success rate trends
- Cost trends
- Token usage trends

#### QA View
- QA rejection rates
- Common issues found by QA
- Average iterations to approval
- QA session statistics

## Data Processing

### Spec Discovery
The service scans `.auto-claude/specs/` for all task directories and loads:
- `implementation_plan.json` - Primary metadata source
- `cost_report.json` - Cost and token data
- `attempt_history.json` - Execution attempts
- `qa_report.md` - QA findings

### Metric Aggregation
1. **Load all spec data** from filesystem
2. **Parse JSON/Markdown** files with error handling
3. **Aggregate metrics** across all specs
4. **Calculate derived metrics** (averages, percentages, trends)
5. **Return structured data** via dataclass models

### Error Handling
- Missing files are skipped gracefully
- JSON parse errors are logged and ignored
- Invalid data is filtered out
- Service returns partial data if some specs fail to load

## Configuration

The service is configured through the AnalyticsService constructor:

```python
service = AnalyticsService(
    specs_dir=Path(".auto-claude/specs"),  # Where to find spec directories
)
```

The `specs_dir` should point to the directory containing all task spec folders (e.g., `001-feature-name/`, `002-bug-fix/`).

## Performance Considerations

- **Lazy Loading**: Data is loaded on-demand when methods are called
- **Caching**: Consider implementing caching if calling multiple times
- **File I/O**: Scans all spec directories - may be slow with many tasks
- **Memory**: Loads all spec data into memory - consider pagination for very large datasets

## Internationalization

The frontend Analytics component supports multiple languages:
- English (`en/analytics.json`)
- French (`fr/analytics.json`)

Add translations for new languages in `apps/frontend/src/shared/i18n/locales/`.

## Security

- **No Sensitive Data**: Analytics contain aggregated metrics only, no PII
- **Read-Only**: Service only reads data, never modifies specs
- **Input Sanitization**: All file paths are validated
- **IPC Protection**: Data transferred via secure Electron IPC

## Testing

To test the analytics service:

```python
# Unit test example
from apps.backend.services.analytics import AnalyticsService
from pathlib import Path

service = AnalyticsService(specs_dir=Path("test_specs"))
summary = service.get_metrics_summary()
assert summary.total_specs >= 0
assert 0 <= summary.overall_success_rate <= 100
```

## Future Enhancements

Potential improvements:
- **Real-time Updates**: WebSocket streaming of live analytics
- **Export Functionality**: Export analytics to CSV/Excel
- **Custom Date Ranges**: Flexible time range selection
- **Comparison Views**: Compare performance across projects
- **Agent Leaderboard**: Rank agents by performance metrics
- **Cost Forecasting**: Predict future costs based on trends
- **Anomaly Detection**: Alert on unusual patterns or performance drops

## Related Documentation

- **Frontend Component**: `apps/frontend/src/renderer/components/Analytics.tsx`
- **IPC Handlers**: `apps/frontend/src/main/ipc-handlers/analytics-handlers.ts`
- **TypeScript Types**: `apps/frontend/src/shared/types/analytics.ts`
- **Preload API**: `apps/frontend/src/preload/api/modules/analytics-api.ts`
- **Backend CLI**: `apps/backend/cli/analytics_cli.py`

## Support

For issues or questions about the Analytics feature:
- Check the implementation plan: `.auto-claude/specs/048-agent-performance-analytics/`
- Review QA report: `.auto-claude/specs/048-agent-performance-analytics/qa_report.md`
- See spec documentation: `.auto-claude/specs/048-agent-performance-analytics/spec.md`
