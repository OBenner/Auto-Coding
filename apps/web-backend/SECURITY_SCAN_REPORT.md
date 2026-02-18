# Security Scan Report - Auto-Claude Web Backend

**Date:** 2026-02-12
**Tool:** Bandit v1.9.3
**Target:** `api/` directory
**Lines of Code:** 2,177

## Summary

| Severity | Count | Status |
|----------|-------|--------|
| HIGH | 0 | ✅ Pass |
| MEDIUM | 1 | ⚠️ Reviewed |
| LOW | 3 | ⚠️ Reviewed |

**Result: PASS** - No high severity issues found.

## Findings Analysis

### 1. B106 - Hardcoded Password (LOW, FALSE POSITIVE)

**Files:** `api/routes/users.py` (lines 92, 162)
**Finding:** `token_type="bearer"` flagged as potential hardcoded password.
**Analysis:** This is a standard OAuth2 token type identifier, not a password. The string "bearer" is defined in RFC 6750 as the token type for Bearer Token Authentication.
**Resolution:** Added `# nosec B106` with explanation.

### 2. B604 - Shell Parameter (MEDIUM, INTENTIONAL)

**File:** `api/websocket.py` (line 467)
**Finding:** Function call with `shell=True` parameter.
**Analysis:** This is intentional for the terminal WebSocket feature which requires PTY shell spawning. Security is maintained through:
- JWT authentication required for WebSocket connection
- User claims validated before session creation
- Terminal session isolated to user's working directory

**Resolution:** Added `# nosec B604` with explanation.

### 3. B110 - Try/Except/Pass (LOW, INTENTIONAL)

**File:** `api/websocket.py` (line 561)
**Finding:** Empty except handler detected.
**Analysis:** This is in a cleanup handler during WebSocket disconnection. Silencing errors when sending a final status message is intentional - the client may already be disconnected.
**Resolution:** Added `# nosec B110` with explanation.

## Recommendations

1. **Re-run scan periodically** - Add bandit to CI/CD pipeline
2. **Review new code** - Ensure security annotations are justified
3. **Update dependencies** - Keep security-related packages updated

## Scan Command

```bash
python -m bandit -r api/ -f json
```

## Configuration

See `.bandit` file for scan configuration and exclusion justifications.
