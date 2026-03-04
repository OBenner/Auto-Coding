# End-to-End Verification: Multi-Model Provider Support

## Overview
This document provides comprehensive E2E testing procedures for the multi-model provider support feature. All backend adapters, cost calculation, and UI components have been implemented and unit-tested. This E2E verification ensures the complete integration works as expected.

## Prerequisites

### Environment Setup
1. **Backend Configuration** (`apps/backend/.env`):
   ```bash
   # Claude (Anthropic) - Default provider
   ANTHROPIC_API_KEY=your_key_here

   # OpenAI
   OPENAI_API_KEY=your_key_here
   OPENAI_MODEL=gpt-4o  # Optional, defaults to gpt-4o

   # Google Gemini
   GOOGLE_API_KEY=your_key_here
   GOOGLE_MODEL=gemini-2.0-flash  # Optional

   # Ollama (Local)
   OLLAMA_BASE_URL=http://localhost:11434/v1  # Default
   OLLAMA_MODEL=llama2  # Or any installed model

   # Provider Selection
   AI_ENGINE_PROVIDER=claude  # Options: claude, openai, google, ollama
   ```

2. **Ollama Setup** (for local model testing):
   ```bash
   # Install Ollama from https://ollama.ai
   # Pull a model
   ollama pull llama2
   # Verify it's running
   curl http://localhost:11434/api/tags
   ```

3. **Start Application**:
   ```bash
   npm run dev  # Starts Electron app with remote debugging
   ```

## E2E Test Scenarios

### Scenario 1: Provider Selection UI
**Objective:** Verify provider selection interface works correctly

**Steps:**
1. Start application: `npm run dev`
2. Navigate to Settings (sidebar or hash route `#settings`)
3. Locate "Provider Settings" section
4. Verify UI elements:
   - [ ] Provider dropdown shows all options (Anthropic, OpenAI, Google, Ollama)
   - [ ] Provider cards display for each option
   - [ ] Model lists are expandable
   - [ ] Selected provider info panel shows endpoint and model count

**Expected Results:**
- All providers visible in dropdown
- No console errors
- UI follows design patterns (cards, badges, consistent styling)
- i18n translations display correctly (test both EN and FR)

---

### Scenario 2: Cost Comparison Display
**Objective:** Verify cost data displays accurately

**Steps:**
1. In Settings, locate "Cost Comparison" section
2. Verify pricing display:
   - [ ] Claude models: Opus ($15/$75), Sonnet ($3/$15), Haiku ($0.80/$4)
   - [ ] OpenAI models: GPT-4o ($2.50/$10), GPT-4 ($30/$60), o1 ($15/$60)
   - [ ] Google models: Gemini 2.0 Flash ($0.10/$0.40), 1.5 Pro ($0.15/$0.60)
   - [ ] Ollama models: Free ($0/$0)
3. Check visual indicators:
   - [ ] Cheapest model highlighted with blue badge
   - [ ] Free local models highlighted with green badge
   - [ ] Pricing per 1M tokens clearly labeled

**Expected Results:**
- All pricing data matches backend `cost_calculator.py`
- Visual indicators work correctly
- Information banner explains pricing model

---

### Scenario 3: OpenAI Provider Configuration
**Objective:** Configure and test OpenAI provider

**Steps:**
1. **Configure Backend:**
   ```bash
   # In apps/backend/.env
   AI_ENGINE_PROVIDER=openai
   OPENAI_API_KEY=sk-...  # Your actual key
   OPENAI_MODEL=gpt-4o
   ```

2. **Verify Configuration:**
   ```bash
   cd apps/backend
   python -c "from core.providers.config import get_provider_config; config = get_provider_config(); print(f'Provider: {config.ai_engine_provider}'); print(f'Model: {config.openai_model}')"
   ```
   Expected output:
   ```
   Provider: AIEngineProvider.OPENAI
   Model: gpt-4o
   ```

3. **Test Provider Adapter:**
   ```bash
   python -c "from core.providers.factory import create_engine_provider; from core.providers.config import get_provider_config; config = get_provider_config(); provider = create_engine_provider(config); print(f'Provider created: {type(provider).__name__}')"
   ```
   Expected output:
   ```
   Provider created: OpenAIProvider
   ```

4. **Create Test Spec:**
   ```bash
   python spec_runner.py --task "Add a test button to homepage" --complexity simple
   ```

5. **Run Build with OpenAI:**
   ```bash
   python run.py --spec [spec-number]
   ```

6. **Verify Logs:**
   - [ ] Check logs show "AI Engine Provider: OpenAI (gpt-4o)"
   - [ ] Agent session uses OpenAI model
   - [ ] No errors related to provider initialization

**Expected Results:**
- Spec creation works with OpenAI
- Agent sessions successfully use OpenAI models
- Build progress tracked correctly
- Cost tracking shows OpenAI pricing

---

### Scenario 4: Google Gemini Provider
**Objective:** Configure and test Google Gemini provider

**Steps:**
1. **Configure Backend:**
   ```bash
   # In apps/backend/.env
   AI_ENGINE_PROVIDER=google
   GOOGLE_API_KEY=...  # Your actual key
   GOOGLE_MODEL=gemini-2.0-flash
   ```

2. **Verify Configuration:**
   ```bash
   cd apps/backend
   python -c "from core.providers.config import get_provider_config; config = get_provider_config(); print(f'Provider: {config.ai_engine_provider}'); print(f'Model: {config.google_model}')"
   ```

3. **Test Provider Adapter:**
   ```bash
   python -c "from core.providers.factory import create_engine_provider; from core.providers.config import get_provider_config; config = get_provider_config(); provider = create_engine_provider(config); print(f'Provider created: {type(provider).__name__}')"
   ```
   Expected output:
   ```
   Provider created: GoogleProvider
   ```

4. **Create and Run Test Spec:**
   ```bash
   python spec_runner.py --task "Add console.log test" --complexity simple
   python run.py --spec [spec-number]
   ```

5. **Verify:**
   - [ ] Logs show "AI Engine Provider: Google (gemini-2.0-flash)"
   - [ ] Agent completes task successfully
   - [ ] Cost tracking reflects Google pricing

**Expected Results:**
- Gemini provider initializes correctly
- Agent sessions work with Gemini models
- Streaming responses handled properly

---

### Scenario 5: Ollama Local Model
**Objective:** Test local model provider (no API costs)

**Steps:**
1. **Ensure Ollama Running:**
   ```bash
   ollama serve  # If not already running
   ollama list   # Verify models available
   ```

2. **Configure Backend:**
   ```bash
   # In apps/backend/.env
   AI_ENGINE_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434/v1
   OLLAMA_MODEL=llama2  # Or your installed model
   ```

3. **Verify Configuration:**
   ```bash
   cd apps/backend
   python -c "from core.providers.config import get_provider_config; config = get_provider_config(); print(f'Provider: {config.ai_engine_provider}'); print(f'Model: {config.ollama_model}'); print(f'URL: {config.ollama_base_url}')"
   ```

4. **Test Provider Adapter:**
   ```bash
   python -c "from core.providers.factory import create_engine_provider; from core.providers.config import get_provider_config; config = get_provider_config(); provider = create_engine_provider(config); print(f'Provider: {type(provider).__name__}')"
   ```
   Expected output:
   ```
   Provider: OllamaProvider
   ```

5. **Create and Run Test Spec:**
   ```bash
   python spec_runner.py --task "Simple code comment" --complexity simple
   python run.py --spec [spec-number]
   ```

6. **Verify:**
   - [ ] Logs show "AI Engine Provider: Ollama (llama2)"
   - [ ] Agent works with local model
   - [ ] Cost tracking shows $0.00
   - [ ] No external API calls made

**Expected Results:**
- Ollama provider connects to local server
- Free cost calculation (input: $0, output: $0)
- Agent sessions complete successfully

---

### Scenario 6: Provider Switching
**Objective:** Switch between providers and verify correct usage

**Steps:**
1. **Start with Claude:**
   ```bash
   # apps/backend/.env
   AI_ENGINE_PROVIDER=claude
   ANTHROPIC_API_KEY=...
   ```

2. **Run a test spec:**
   ```bash
   python spec_runner.py --task "Test 1" --complexity simple
   python run.py --spec [spec-1]
   # Verify logs show Claude provider
   ```

3. **Switch to OpenAI:**
   ```bash
   # Update apps/backend/.env
   AI_ENGINE_PROVIDER=openai
   OPENAI_API_KEY=...
   ```

4. **Run another test spec:**
   ```bash
   python spec_runner.py --task "Test 2" --complexity simple
   python run.py --spec [spec-2]
   # Verify logs show OpenAI provider
   ```

5. **Switch to Ollama:**
   ```bash
   # Update apps/backend/.env
   AI_ENGINE_PROVIDER=ollama
   ```

6. **Run third test spec:**
   ```bash
   python spec_runner.py --task "Test 3" --complexity simple
   python run.py --spec [spec-3]
   # Verify logs show Ollama provider
   ```

**Expected Results:**
- Each build uses the configured provider
- No cross-contamination between providers
- Cost tracking reflects correct provider pricing
- Logs clearly indicate which provider is active

---

### Scenario 7: Fallback Configuration
**Objective:** Test fallback model selection

**Steps:**
1. **Configure Primary and Fallback:**
   ```bash
   # apps/backend/.env
   AI_ENGINE_PROVIDER=openai
   OPENAI_MODEL=gpt-4o
   # Fallback configured in UI or model_fallback.py
   ```

2. **Verify Fallback Chain:**
   ```bash
   cd apps/backend
   python -c "from core.model_fallback import get_fallback_model; print('gpt-4o fallback:', get_fallback_model('gpt-4o')); print('opus fallback:', get_fallback_model('claude-opus-4-20250514'))"
   ```
   Expected output:
   ```
   gpt-4o fallback: gpt-4-turbo
   opus fallback: claude-sonnet-4-5-20250929
   ```

3. **Test Fallback UI:**
   - In Settings > Provider Settings
   - Select a provider
   - [ ] Verify fallback model dropdown appears
   - [ ] Select a fallback model
   - [ ] Verify info box explains fallback behavior
   - [ ] Switch provider and verify fallback clears

4. **Simulate Model Unavailable** (optional, requires API manipulation):
   - Configure invalid model name
   - Verify fallback logic triggers
   - Check logs for fallback transition message

**Expected Results:**
- Fallback chains defined for all providers
- UI allows fallback selection per provider
- Fallback triggers when primary model unavailable
- Logs show fallback transition with cost implications

---

### Scenario 8: Cost Estimation Integration
**Objective:** Verify cost calculation across providers

**Steps:**
1. **Test Backend Cost Calculator:**
   ```bash
   cd apps/backend
   python -c "
   from core.providers.cost_calculator import calculate_cost, estimate_session_cost

   # Test OpenAI GPT-4o
   cost = calculate_cost('gpt-4o', input_tokens=10000, output_tokens=2000)
   print(f'GPT-4o (10K in, 2K out): \${cost:.4f}')

   # Test Claude Sonnet
   cost = calculate_cost('claude-sonnet-4-5-20250929', input_tokens=5000, output_tokens=1000)
   print(f'Claude Sonnet (5K in, 1K out): \${cost:.4f}')

   # Test Ollama (free)
   cost = calculate_cost('llama2', input_tokens=10000, output_tokens=2000)
   print(f'Ollama llama2 (10K in, 2K out): \${cost:.4f}')
   "
   ```
   Expected output:
   ```
   GPT-4o (10K in, 2K out): $0.0450
   Claude Sonnet (5K in, 1K out): $0.0300
   Ollama llama2 (10K in, 2K out): $0.0000
   ```

2. **Test Frontend Cost Display:**
   - Open app, navigate to Settings > Cost Comparison
   - [ ] Verify all prices match backend calculator
   - [ ] Test model comparison functionality
   - [ ] Verify cheapest/free badges appear correctly

**Expected Results:**
- Backend and frontend cost data match exactly
- Cost calculation works for all providers
- Ollama always shows $0.00
- Cost estimates accurate for typical usage

---

## Automated Verification Script

A Python script is provided for automated verification:

```bash
cd apps/backend
python .auto-claude/specs/147-multi-model-provider-support-architecture/verify_e2e.py
```

This script runs all backend verification tests automatically.

---

## Acceptance Criteria Checklist

### Backend Implementation
- [x] OpenAI provider adapter created and functional
- [x] Google Gemini provider adapter created and functional
- [x] Ollama provider adapter created and functional
- [x] Cost calculator supports all providers
- [x] Fallback model chains defined
- [x] Provider factory creates correct adapter instances

### Frontend Implementation
- [x] Provider selection UI in settings
- [x] Cost comparison component displays pricing
- [x] Fallback model selector in provider settings
- [x] Settings store persists provider configuration
- [x] IPC handlers sync provider config with backend
- [x] i18n translations for all new UI elements

### Integration
- [x] Backend client.py aware of configured provider
- [x] Provider config syncs between frontend and backend
- [ ] **E2E verification completed** ← This document provides the test plan

### Testing
- [ ] OpenAI provider tested with real API key
- [ ] Google Gemini provider tested with real API key
- [ ] Ollama provider tested with local model
- [ ] Provider switching works correctly
- [ ] Fallback model selection functional
- [ ] Cost tracking accurate across providers

---

## Troubleshooting

### Issue: Provider not found
**Solution:** Verify `AI_ENGINE_PROVIDER` in `.env` matches enum values:
```python
# Valid values:
AI_ENGINE_PROVIDER=claude      # AIEngineProvider.CLAUDE
AI_ENGINE_PROVIDER=openai      # AIEngineProvider.OPENAI
AI_ENGINE_PROVIDER=google      # AIEngineProvider.GOOGLE
AI_ENGINE_PROVIDER=ollama      # AIEngineProvider.OLLAMA
```

### Issue: OpenAI authentication failed
**Solution:** Check API key format:
```bash
# Must start with 'sk-'
OPENAI_API_KEY=sk-proj-...
```

### Issue: Ollama connection refused
**Solution:** Ensure Ollama is running:
```bash
ollama serve
# In another terminal:
curl http://localhost:11434/api/tags
```

### Issue: Google API key invalid
**Solution:** Verify API key and enabled services:
```bash
# Check AI Studio: https://aistudio.google.com/apikey
# Ensure Gemini API is enabled in your Google Cloud project
```

---

## Success Criteria

This E2E verification is considered complete when:
1. ✅ All 8 test scenarios pass
2. ✅ Automated verification script runs without errors
3. ✅ All acceptance criteria checkboxes are marked
4. ✅ No console errors in frontend
5. ✅ Provider switching works seamlessly
6. ✅ Cost tracking accurate for all providers

---

## Notes

- **Security:** API keys should NEVER be committed to version control
- **Cost Management:** Use Ollama for development to avoid API costs
- **Performance:** Local models (Ollama) are slower but free
- **Model Selection:** Choose provider based on task requirements:
  - Claude: Best for code generation and reasoning
  - GPT-4o: Fast and cost-effective
  - Gemini: Google ecosystem integration
  - Ollama: Free, private, offline-capable

---

**Document Version:** 1.0
**Last Updated:** 2026-02-13
**Status:** Ready for E2E verification
