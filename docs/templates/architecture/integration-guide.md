# [Integration Name] Integration

<!--
INSTRUCTIONS: Replace [Integration Name] with the third-party service name (e.g., "Graphiti Memory", "Linear", "GitHub API")
This template helps you document external integrations following Auto Claude's documentation patterns.
Fill in each section below, removing placeholder comments when done.
-->

[One-sentence description of what this integration provides and why it's needed]

## Overview

<!--
INSTRUCTIONS: Provide a brief overview of the integration.
Explain what the external service does and how it integrates with Auto Claude.
-->

**Integration Type:** [API/SDK/MCP Server/Database/Service]
**Provider:** [Company/Organization name]
**Status:** [Required/Optional/Experimental]
**Documentation:** [Link to official docs]

### Purpose

[Explain the business/technical purpose of this integration. What capabilities does it add?]

### Key Features

- [Feature 1 provided by this integration]
- [Feature 2 provided by this integration]
- [Feature 3 provided by this integration]

## Prerequisites

<!--
INSTRUCTIONS: List everything needed before setting up the integration.
Include accounts, API keys, system requirements, etc.
-->

### Required

- [ ] [Account type] account with [Provider] ([Sign-up link])
- [ ] [API key/credentials] ([Where to obtain])
- [ ] [System requirement - e.g., Python 3.12+, Node.js 18+]
- [ ] [Other dependencies]

### Optional

- [ ] [Optional enhancement 1]
- [ ] [Optional enhancement 2]

## Configuration

<!--
INSTRUCTIONS: Document all configuration steps in order.
Include environment variables, config files, and setup commands.
-->

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INTEGRATION_ENABLED` | Yes | `false` | Enables the integration |
| `INTEGRATION_API_KEY` | Yes | - | API key from provider |
| `INTEGRATION_BASE_URL` | No | `https://api.provider.com` | API endpoint URL |
| `INTEGRATION_TIMEOUT` | No | `30` | Request timeout in seconds |

### Configuration File

**Location:** `apps/backend/[config-file].py` or `.env`

```bash
# .env configuration example
INTEGRATION_ENABLED=true
INTEGRATION_API_KEY=your_api_key_here
INTEGRATION_BASE_URL=https://api.provider.com
INTEGRATION_TIMEOUT=30

# Optional settings
INTEGRATION_OPTION_1=value
INTEGRATION_OPTION_2=value
```

### Setup Steps

1. **Obtain API credentials:**
   ```bash
   # Navigate to provider dashboard
   # Generate API key: [URL or instructions]
   ```

2. **Configure environment:**
   ```bash
   # Copy environment template
   cp apps/backend/.env.example apps/backend/.env

   # Edit .env and add your credentials
   # INTEGRATION_API_KEY=your_key_here
   ```

3. **Install dependencies:**
   ```bash
   cd apps/backend
   uv pip install -r requirements.txt
   ```

4. **Verify setup:**
   ```bash
   # Test connection
   python -c "from integrations.[integration_name] import verify_connection; verify_connection()"
   ```

## Architecture

<!--
INSTRUCTIONS: Show how the integration fits into Auto Claude's architecture.
Include file structure and component relationships.
-->

### Integration Structure

```
apps/backend/integrations/[integration_name]/
├── __init__.py              # Public API exports
├── config.py                # Configuration and validation
├── client.py                # API client wrapper
├── [feature].py             # Core functionality
├── utils.py                 # Helper functions
└── README.md                # Integration-specific docs
```

### Key Components

#### `config.py`
- Validates environment variables
- Provides configuration object
- Handles provider-specific settings

#### `client.py`
- API client wrapper
- Connection management
- Request/response handling
- Error translation

#### `[feature].py`
- Core integration functionality
- Business logic
- Data transformation

#### `utils.py`
- Helper functions
- Data validation
- Type conversions

### Integration Points

<!--
INSTRUCTIONS: Document where in Auto Claude this integration is used.
List the files/modules that call the integration.
-->

| Location | Purpose | Usage |
|----------|---------|-------|
| `apps/backend/agents/[agent].py` | [Agent integration] | [How agent uses it] |
| `apps/backend/core/[module].py` | [Core integration] | [How core uses it] |
| `apps/backend/cli/[command].py` | [CLI integration] | [How CLI uses it] |

## Usage

<!--
INSTRUCTIONS: Provide practical code examples showing how to use the integration.
Include common patterns and best practices.
-->

### Basic Usage

```python
from integrations.[integration_name] import IntegrationClient

# Initialize client
client = IntegrationClient(
    api_key="your_api_key",
    base_url="https://api.provider.com"
)

# Basic operation
result = client.basic_operation(param1="value1")
print(result)
```

### Advanced Usage

```python
from integrations.[integration_name] import (
    IntegrationClient,
    AdvancedFeature,
    ConfigOptions
)

# Configure client with custom options
config = ConfigOptions(
    timeout=60,
    retry_attempts=3,
    enable_caching=True
)

client = IntegrationClient(config=config)

# Use advanced features
feature = AdvancedFeature(client)
result = feature.complex_operation(
    param1="value1",
    param2="value2",
    options={"key": "value"}
)
```

### Common Patterns

#### Pattern 1: [Pattern Name]

```python
# [Description of what this pattern does]
from integrations.[integration_name] import pattern_function

result = pattern_function(
    input_data=data,
    options=options
)
```

#### Pattern 2: [Pattern Name]

```python
# [Description of what this pattern does]
from integrations.[integration_name] import PatternClass

with PatternClass() as context:
    result = context.perform_operation()
```

## Authentication

<!--
INSTRUCTIONS: Document authentication methods in detail.
Include token refresh, credential storage, and security best practices.
-->

### Authentication Method

[Describe the authentication method: API Key, OAuth 2.0, JWT, etc.]

### Credential Storage

**CRITICAL: Never commit credentials to version control**

Credentials are stored in:
- **Development:** `.env` file (gitignored)
- **Production:** Environment variables or secret management system

### Token Management

```python
from integrations.[integration_name].auth import AuthManager

# Initialize auth manager
auth = AuthManager(api_key="your_key")

# Tokens are automatically refreshed
client = IntegrationClient(auth=auth)
```

### Security Best Practices

1. **Use environment variables:** Store API keys in `.env`, never in code
2. **Rotate credentials regularly:** Update API keys periodically
3. **Minimum permissions:** Use API keys with minimal required scopes
4. **Secure transmission:** All requests use HTTPS
5. **Error handling:** Don't log sensitive data in error messages

## API Reference

<!--
INSTRUCTIONS: Document key API methods available through this integration.
Focus on methods users will call, not internal implementation details.
-->

### Client Methods

#### `client.method_name(param1, param2, **options)`

**Purpose:** [What this method does]

**Parameters:**
- `param1` (type): [Description]
- `param2` (type): [Description]
- `**options`: Optional configuration

**Returns:** [Return type and description]

**Example:**
```python
result = client.method_name(
    param1="value",
    param2=123,
    timeout=30
)
```

**Raises:**
- `IntegrationError`: [When this is raised]
- `AuthenticationError`: [When this is raised]
- `RateLimitError`: [When this is raised]

### Data Models

#### `ResponseModel`

```python
@dataclass
class ResponseModel:
    """[Description of what this model represents]"""

    field1: str          # [Description]
    field2: int          # [Description]
    field3: Optional[str] = None  # [Description]
```

## Error Handling

<!--
INSTRUCTIONS: Document error types, common errors, and how to handle them.
-->

### Error Types

```python
from integrations.[integration_name].exceptions import (
    IntegrationError,      # Base exception
    AuthenticationError,   # Auth failures
    RateLimitError,        # Rate limit exceeded
    ValidationError,       # Invalid input
    ConnectionError,       # Network issues
)
```

### Error Handling Pattern

```python
from integrations.[integration_name] import IntegrationClient
from integrations.[integration_name].exceptions import (
    IntegrationError,
    RateLimitError
)

client = IntegrationClient()

try:
    result = client.operation()
except RateLimitError as e:
    # Handle rate limiting
    print(f"Rate limit exceeded. Retry after: {e.retry_after}")
    time.sleep(e.retry_after)
    result = client.operation()
except IntegrationError as e:
    # Handle general errors
    print(f"Integration error: {e}")
    raise
```

### Common Errors

#### Error: `Authentication failed`

**Cause:** Invalid or expired API key

**Solution:**
1. Verify API key in `.env` file
2. Check API key has not expired
3. Regenerate key from provider dashboard

#### Error: `Rate limit exceeded`

**Cause:** Too many requests in short time period

**Solution:**
1. Implement exponential backoff
2. Reduce request frequency
3. Contact provider for higher rate limits

## Testing

<!--
INSTRUCTIONS: Explain how to test the integration.
Include unit tests, integration tests, and manual testing procedures.
-->

### Running Tests

```bash
# Run all integration tests
pytest tests/integrations/test_[integration_name].py -v

# Run specific test
pytest tests/integrations/test_[integration_name].py::test_client_connection -v

# Run with live API (requires valid credentials)
pytest tests/integrations/test_[integration_name].py --live-api
```

### Test Coverage

Tests verify:
- ✅ Configuration validation
- ✅ Authentication flow
- ✅ Basic operations
- ✅ Error handling
- ✅ Rate limiting
- ✅ Data transformation
- ✅ Connection retry logic

### Manual Testing

```bash
# Test connection
python scripts/test_integration.py --integration [integration_name] --test connection

# Test basic operation
python scripts/test_integration.py --integration [integration_name] --test operation
```

## Monitoring & Observability

<!--
INSTRUCTIONS: Document how to monitor the integration's health and performance.
OPTIONAL: Remove if not applicable.
-->

### Key Metrics

- **Request count:** Number of API calls made
- **Success rate:** Percentage of successful requests
- **Response time:** Average API response time
- **Error rate:** Percentage of failed requests
- **Rate limit usage:** Current usage vs. limit

### Logging

```python
import logging

logger = logging.getLogger("integrations.[integration_name]")

# Logs include:
# - Request/response details (excluding sensitive data)
# - Error messages and stack traces
# - Performance metrics
```

### Health Checks

```python
from integrations.[integration_name] import health_check

# Verify integration is healthy
status = health_check()
# Returns: {"status": "healthy", "latency_ms": 150}
```

## Performance Considerations

<!--
INSTRUCTIONS: Document performance characteristics and optimization tips.
OPTIONAL: Remove if not applicable.
-->

### Rate Limits

| Tier | Requests/min | Requests/day | Notes |
|------|--------------|--------------|-------|
| Free | [number] | [number] | [Limitations] |
| Pro | [number] | [number] | [Benefits] |
| Enterprise | [number] | [number] | [Custom limits] |

### Optimization Tips

1. **Batch requests:** Combine multiple operations when possible
2. **Cache responses:** Cache frequently accessed data
3. **Use webhooks:** Subscribe to events instead of polling
4. **Implement retry logic:** Handle transient failures gracefully
5. **Monitor usage:** Track API usage to avoid rate limits

### Caching Strategy

```python
from integrations.[integration_name] import CachedClient

# Enable caching
client = CachedClient(
    cache_ttl=300,  # 5 minutes
    cache_backend="redis"
)
```

## Troubleshooting

<!--
INSTRUCTIONS: Document common issues and solutions.
Include debugging tips and diagnostic commands.
-->

### Debug Mode

Enable debug logging for detailed information:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("integrations.[integration_name]")
logger.setLevel(logging.DEBUG)
```

### Common Issues

#### Issue: Connection timeout

**Symptom:** Requests hang or timeout after 30 seconds

**Diagnosis:**
```bash
# Check network connectivity
curl https://api.provider.com/health
```

**Solution:**
- Increase timeout: `INTEGRATION_TIMEOUT=60`
- Check firewall rules
- Verify API endpoint URL

#### Issue: Invalid response format

**Symptom:** `ValidationError: Unexpected response format`

**Diagnosis:**
```python
# Enable response logging
client = IntegrationClient(log_responses=True)
```

**Solution:**
- Update integration to latest version
- Check provider API version
- Contact support if format changed

### Diagnostic Commands

```bash
# Test configuration
python -c "from integrations.[integration_name].config import validate_config; validate_config()"

# Test connection
python -c "from integrations.[integration_name] import test_connection; test_connection()"

# Check credentials
python -c "from integrations.[integration_name].auth import verify_credentials; verify_credentials()"
```

## Migration Guide

<!--
INSTRUCTIONS: If this replaces an older integration, provide migration steps.
For new integrations, document how to adopt it in existing code.
-->

### Adopting in Existing Code

```python
# Before (without integration)
# Manual API calls or alternative solution

# After (with integration)
from integrations.[integration_name] import IntegrationClient

client = IntegrationClient()
result = client.operation()
```

### Breaking Changes

[Document any breaking changes from previous versions]

**Version X.X.X → Y.Y.Y:**
- [Change 1]: [How to migrate]
- [Change 2]: [How to migrate]

## Cost Considerations

<!--
INSTRUCTIONS: Document pricing and cost implications.
OPTIONAL: Remove if free/open-source integration.
-->

### Pricing Tiers

| Tier | Monthly Cost | Included Usage | Overage Cost |
|------|--------------|----------------|--------------|
| Free | $0 | [X requests/month] | N/A |
| Pro | $XX | [Y requests/month] | $X per 1K requests |
| Enterprise | Custom | Unlimited | N/A |

### Cost Optimization

- [Tip 1 for reducing costs]
- [Tip 2 for reducing costs]
- [Tip 3 for reducing costs]

## Related Documentation

<!--
INSTRUCTIONS: Link to related documentation that users might need.
-->

- [Provider Official Documentation]([URL])
- [API Reference]([URL])
- [Integration Changelog](./CHANGELOG.md)
- [Auto Claude Architecture Documentation](../../CLAUDE.md)
- [Related Integration Guide](./related-integration-guide.md)

## Support & Resources

<!--
INSTRUCTIONS: Provide support channels and additional resources.
-->

### Provider Support

- **Documentation:** [Provider docs URL]
- **Support Portal:** [Support URL]
- **Status Page:** [Status page URL]
- **Community:** [Forum/Discord/Slack URL]

### Auto Claude Support

- **Issues:** [GitHub issues for integration]
- **Discussions:** [GitHub discussions]
- **Contributing:** See [CONTRIBUTING.md](../../../CONTRIBUTING.md)

## Changelog

<!--
INSTRUCTIONS: Document significant changes to the integration.
OPTIONAL: Can link to separate CHANGELOG.md instead.
-->

### Version [X.X.X] - [YYYY-MM-DD]

**Added:**
- [New feature 1]
- [New feature 2]

**Changed:**
- [Changed behavior 1]

**Fixed:**
- [Bug fix 1]

### Version [X.X.X] - [YYYY-MM-DD]

**Added:**
- Initial integration

## Contributing

<!--
INSTRUCTIONS: Guidelines for contributing to this integration.
OPTIONAL: Remove if not accepting contributions.
-->

Contributions to improve this integration are welcome!

**Areas for contribution:**
- [ ] Additional features
- [ ] Performance optimizations
- [ ] Better error handling
- [ ] Expanded test coverage
- [ ] Documentation improvements

See [CONTRIBUTING.md](../../../CONTRIBUTING.md) for guidelines.

---

**Document Information:**
- **Template Version:** 1.0
- **Last Updated:** [YYYY-MM-DD]
- **Maintainer:** [Team/Person responsible for this integration]
- **Integration Version:** [X.X.X]
- **Provider API Version:** [X.X]
