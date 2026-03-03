# Manual E2E Test Procedure for GLM Provider

## Quick Start

This document provides step-by-step instructions for running the end-to-end test of the GLM (Zhipu AI) provider integration.

## Prerequisites

1. **ZhipuAI API Key** (Free tier available)
   - Sign up at: https://open.bigmodel.cn/
   - Get API key from console
   - Free model `glm-4-flash-250414` has generous free tier

2. **Python Environment**
   - Python 3.12+
   - Dependencies installed: `pip install -r requirements.txt`

3. **Project Setup**
   - Auto Code repository cloned
   - In the worktree: `tasks/139-add-runtime-provider-and-model-selection`

## Test Procedure

### Step 1: Set API Key

**Linux/macOS:**
```bash
export ZHIPUAI_API_KEY=your_actual_api_key_here
```

**Windows (PowerShell):**
```powershell
$env:ZHIPUAI_API_KEY="your_actual_api_key_here"
```

**Windows (CMD):**
```cmd
set ZHIPUAI_API_KEY=your_actual_api_key_here
```

### Step 2: Run Automated Test Suite

```bash
# From the worktree root
python tests/e2e/test_glm_provider_e2e.py
```

**Expected Output:**
```
✓ --provider flag available in CLI
✓ zhipuai listed as provider choice
✓ --model flag available in CLI
✓ zhipuai available in provider factory
✓ Provider factory creates zhipuai provider successfully
✓ All automated checks passed
```

### Step 3: Run Manual E2E Test

```bash
cd apps/backend

python run.py --spec 139-e2e-glm-test \
    --provider zhipuai \
    --model glm-4-flash-250414 \
    --verbose
```

**What to Look For:**

1. **Provider Selection:**
   - Logs should show: "Using provider: zhipuai"
   - Logs should show: "Using model: glm-4-flash-250414"

2. **Task Execution:**
   - Agent should create `hello_glm.py` file
   - Task should complete successfully
   - No errors in logs

3. **File Verification:**
   ```bash
   # Check file exists
   ls hello_glm.py

   # Run the script
   python hello_glm.py

   # Expected output:
   # Hello from GLM!
   ```

### Step 4: Verify Configuration Persistence

```bash
# Check that provider config was saved
cat .auto-claude/specs/139-e2e-glm-test/implementation_plan.json

# Look for provider_config section:
# "provider_config": {
#   "provider": "zhipuai",
#   "model": "glm-4-flash-250414"
# }
```

### Step 5: Test Task Restart (Optional)

```bash
# Restart the task (should skip completed subtasks)
python run.py --spec 139-e2e-glm-test \
    --provider zhipuai \
    --model glm-4-flash-250414 \
    --restart-from subtask-1-1
```

**Expected Behavior:**
- Should indicate subtask-1-1 is already completed
- Should preserve provider/model configuration from previous run

## Verification Checklist

Use this checklist to verify the test passes:

- [ ] API key is set (`echo $ZHIPUAI_API_KEY` shows value)
- [ ] Automated test suite passes (all checks show ✓)
- [ ] Task execution starts with zhipuai provider
- [ ] Logs show "Using provider: zhipuai"
- [ ] Logs show "Using model: glm-4-flash-250414"
- [ ] Task completes successfully
- [ ] `hello_glm.py` file is created
- [ ] `python hello_glm.py` outputs "Hello from GLM!"
- [ ] `implementation_plan.json` contains `provider_config` section
- [ ] Task restart preserves provider/model configuration

## Troubleshooting

### Issue: "ZHIPUAI_API_KEY not set"

**Solution:** Set the environment variable (see Step 1)

### Issue: "Provider 'zhipuai' not found"

**Solution:**
- Verify `zai-sdk` package is installed: `pip list | grep zai`
- Install if missing: `pip install zai-sdk>=0.2.2`

### Issue: "Invalid API key"

**Solution:**
- Verify API key is correct
- Check for extra spaces or quotes
- Regenerate API key from ZhipuAI console if needed

### Issue: "Rate limit exceeded"

**Solution:**
- Free tier has rate limits
- Wait a few minutes and retry
- Consider upgrading to paid tier for testing

### Issue: "Network error"

**Solution:**
- Check internet connection
- Verify firewall allows access to ZhipuAI API
- Check if VPN is blocking the connection

### Issue: "Task did not complete"

**Solution:**
- Check verbose output for errors
- Verify all dependencies are installed
- Check Python version (3.12+ required)

## Expected Results Summary

**Success Criteria:**
1. ✅ Automated tests pass (5/5 checks)
2. ✅ Task executes with zhipuai provider
3. ✅ GLM-4-Flash model is used
4. ✅ hello_glm.py file is created
5. ✅ Script outputs "Hello from GLM!"
6. ✅ Provider config is persisted
7. ✅ Task restart preserves configuration

**Test Duration:**
- Automated tests: < 1 minute
- Manual E2E test: 2-5 minutes (depends on API response time)

## Cleanup

After testing, clean up the test spec:

```bash
# Remove test spec directory
rm -rf .auto-claude/specs/139-e2e-glm-test

# Remove created file (if exists)
rm -f hello_glm.py
```

## Next Steps

If the test passes:
1. ✅ GLM provider integration is verified
2. ✅ Ready for production use
3. ✅ Update documentation with API key setup instructions
4. ✅ Add to CI/CD (optional, with mocked tests)

If the test fails:
1. Check error messages in verbose output
2. Review troubleshooting section
3. Check implementation_plan.json for configuration issues
4. Verify all dependencies are installed

---

**Last Updated:** 2025-02-07
**Test Spec:** 139-e2e-glm-test
**Provider:** zhipuai (Zhipu AI)
**Model:** glm-4-flash-250414 (Free tier)
