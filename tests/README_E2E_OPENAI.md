# OpenAI Provider E2E Test Documentation

This document describes the E2E test suite for OpenAI provider integration in Auto Claude.

## Test File

**Location:** `tests/test_openai_provider_e2e.py`

## Overview

The E2E test validates the complete flow of configuring and using OpenAI GPT-4 models via LiteLLM provider, including:

- Provider configuration via environment variables
- OpenAI API key management
- Cost tracking for GPT-4 models
- Per-agent provider selection
- Mixed Claude/OpenAI usage scenarios

## Running the Tests

### Automated Tests (Mocked API)

Fast, offline tests that use mocked OpenAI responses:

```bash
# Run all tests
pytest tests/test_openai_provider_e2e.py -v

# Run specific test class
pytest tests/test_openai_provider_e2e.py::TestE2EOpenAIIntegration -v

# Run mocked E2E test
pytest tests/test_openai_provider_e2e.py::TestE2EOpenAIIntegration::test_e2e_openai_provider_mock -v
```

### Live API Tests

Tests that make actual OpenAI API calls (requires valid API key):

```bash
# Set API key
export OPENAI_API_KEY=sk-proj-...

# Run live test
pytest tests/test_openai_provider_e2e.py::TestE2EOpenAIIntegration::test_e2e_openai_provider_live -v
```

**Note:** Live tests are automatically skipped if `OPENAI_API_KEY` is not set.

## Manual Test Procedure

For full UI-based testing, run:

```bash
python tests/test_openai_provider_e2e.py
```

This will print a detailed manual test procedure including:
1. Opening settings page in Electron app
2. Configuring OpenAI provider
3. Creating and running a test task
4. Verifying cost tracking
5. Success criteria checklist

## Test Coverage

### Provider Configuration Tests

- `TestOpenAIProviderConfiguration`
  - Provider config loaded from environment
  - API key validation

### Cost Tracking Tests

- `TestOpenAICostTracking`
  - GPT-4 pricing definitions
  - Cost calculation accuracy
  - Multi-model cost tracking

### Provider Factory Tests

- `TestOpenAIProviderFactory`
  - LiteLLM provider creation
  - Configuration validation

### E2E Integration Tests

- `TestE2EOpenAIIntegration`
  - Full workflow with mocked API
  - Optional live API integration
  - Per-agent provider selection
  - Mixed Claude/OpenAI scenarios

## Validation

After running a manual test, validate the results:

```bash
python .auto-claude/specs/046-multi-model-provider-support/validate_openai_e2e.py --spec-id <SPEC_ID>
```

This will verify:
- `.env` configuration is correct
- `cost_report.json` exists and is valid
- GPT-4 usage is tracked
- Costs are calculated correctly

## Expected Results

All tests should pass with these conditions met:

✅ Provider configuration loads from environment variables
✅ OpenAI API key is validated
✅ GPT-4 pricing is defined in MODEL_PRICING
✅ Cost calculations are accurate
✅ cost_report.json tracks GPT-4 usage
✅ Per-agent provider selection works
✅ Mixed Claude/OpenAI usage is supported

## Files Created

- `tests/test_openai_provider_e2e.py` - Automated test suite
- `tests/README_E2E_OPENAI.md` - This documentation
- `.auto-claude/specs/046/E2E_TEST_OPENAI.md` - Detailed manual procedure (gitignored)
- `.auto-claude/specs/046/validate_openai_e2e.py` - Validation script (gitignored)

## Related Documentation

- Provider Configuration: `apps/backend/.env.example`
- Cost Tracking: `apps/backend/core/cost_tracking.py`
- Provider Factory: `apps/backend/core/providers/factory.py`
- Settings UI: `apps/frontend/src/renderer/components/settings/ProviderSettingsSection.tsx`

## Troubleshooting

### Import Errors

If you get import errors, ensure you're running from the project root:

```bash
cd /path/to/Auto-Claude
pytest tests/test_openai_provider_e2e.py -v
```

### Missing Dependencies

Install test dependencies:

```bash
pip install -r tests/requirements-test.txt
```

### pytest Not Found

If pytest is not available in your environment:

```bash
python -m pytest tests/test_openai_provider_e2e.py -v
```

Or run the test file directly to see the manual procedure:

```bash
python tests/test_openai_provider_e2e.py
```

## Next Steps

After completing this E2E test:
1. Proceed to subtask-7-2: Ollama provider E2E test
2. Proceed to subtask-7-3: Per-agent provider selection test
3. Update QA acceptance in implementation_plan.json
