# Frontend Secret Patterns Documentation

## Overview

This document describes frontend-specific secret patterns that should be detected by the secret scanner. Frontend secrets are particularly dangerous because they ship to end users and can be extracted from distributed applications (especially Electron apps).

## Pattern Categories

### 1. Browser Storage Patterns

**Risk Level: HIGH**

Browser storage APIs are commonly used to store authentication tokens and API keys. While often used legitimately (storing user tokens after OAuth flow), hardcoded values in these calls indicate accidental credential exposure.

#### localStorage.setItem

**Pattern:**

```javascript
localStorage.setItem('apiKey', 'sk-1234567890abcdef...')
localStorage.setItem('token', 'ghp_1234567890abcdef...')
```

**Detection Regex:**

```regex
localStorage\.setItem\s*\(\s*["\'](?:api[_-]?key|apikey|token|access[_-]?token|auth[_-]?token|secret|api_secret|bearer)["\']\s*,\s*["\']([a-zA-Z0-9_-]{20,})["\']
```

**Key indicators:**
- Method: `localStorage.setItem`
- Key names: apiKey, token, accessToken, authToken, secret, api_secret, bearer
- Value: 20+ character alphanumeric string

#### sessionStorage.setItem

**Pattern:**

```javascript
sessionStorage.setItem('sessionToken', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...')
```

**Detection Regex:**

```regex
sessionStorage\.setItem\s*\(\s*["\'](?:api[_-]?key|apikey|token|access[_-]?token|auth[_-]?token|secret|api_secret|bearer)["\']\s*,\s*["\']([a-zA-Z0-9_-]{20,})["\']
```

**Key indicators:**
- Method: `sessionStorage.setItem`
- Same key names as localStorage
- Value: 20+ character alphanumeric string

### 2. Window Configuration Objects

**Risk Level: HIGH**

Web applications often expose configuration through global `window` objects. These can accidentally contain secrets instead of using environment variables.

#### window.config / window.CONFIG

**Pattern:**

```javascript
window.config = {
  apiKey: 'sk-1234567890abcdef...',
  apiSecret: 'secret_1234567890'
}

window.config.apiKey = 'sk-1234567890abcdef...'
```

**Detection Regex (property assignment):**

```regex
window\.(?:config|CONFIG|appConfig|APP_CONFIG)(?:\.\s*(?:api[_-]?key|apikey|token|access[_-]?token|auth[_-]?token|secret|api_secret|bearer|aws[_-]?key)\s*)?[:=]\s*["\']([a-zA-Z0-9_-]{16,})["\']
```

**Detection Regex (object literal):**

```regex
window\.(?:config|CONFIG|appConfig|APP_CONFIG)\s*=\s*{[^}]*?(?:api[_-]?key|apikey|token|access[_-]?token|auth[_-]?token|secret|api_secret|bearer|aws[_-]?key)\s*:\s*["\']?([a-zA-Z0-9_-]{16,})["\']?
```

**Key indicators:**
- Property names: config, CONFIG, appConfig, APP_CONFIG
- Direct assignment or object property assignment
- 16+ character alphanumeric string

### 3. Environment Variable Patterns

#### import.meta.env (Vite Applications)

**Risk Level: MEDIUM**

Vite applications use `import.meta.env` to access environment variables. The variable reference itself is safe, but hardcoded values should still be caught.

**Safe Pattern (False Positive):**

```javascript
const apiKey = import.meta.env.VITE_API_KEY;  // Safe - reads from .env
```

**Unsafe Pattern (Should be caught by generic patterns):**

```javascript
const apiKey = 'sk-1234567890abcdef...';  // Should be caught
```

**Detection:**
- The scanner has a specific pattern to flag `import.meta.env` usage for review
- False positive filter allows safe `import.meta.env.VARIABLE_NAME` references
- Generic patterns should catch actual hardcoded values

**False Positive Pattern:**

```regex
import\.meta\.env\.[A-Z_]+
```

#### process.env (Electron Main Process)

**Risk Level: HIGH**

Electron main process can access Node.js environment variables through `process.env`.

**Safe Pattern (False Positive):**

```typescript
const dsn = process.env.SENTRY_DSN;  // Safe - reads from environment
```

**Unsafe Pattern:**

```typescript
process.env.API_KEY = 'sk-1234567890abcdef...';  // Hardcoded assignment
```

**Detection Regex:**

```regex
process\.env\.[A-Z_]+\s*=\s*["\']([a-zA-Z0-9_-]{20,})
```

**Read vs. Write Detection:**

The scanner distinguishes between safe reads and unsafe assignments using regex:
- **Assignment** (unsafe): `process\.env\.[A-Z_]+\s*=[^=]` — single `=` not followed by another `=`
- **Read** (safe): `process\.env\.[A-Z_]+(\s|\)|,|;|$)` — variable used in expression context

This correctly handles comparison operators (`==`, `===`) which are not assignments.

#### Build-time Defines (Vite/Webpack)

**Risk Level: LOW**

Build tools often replace variables at build time using `define` options. These appear as global variables:

**Pattern:**

```javascript
const dsn = __SENTRY_DSN__;  // Vite define replacement
```

**Detection:**
- Pattern: `__VARIABLE_NAME__` format
- These are generally safe if values come from CI/CD secrets
- False positive filter: `__[\w_]+__`

### 4. Configuration File Patterns

#### .env Files

**Risk Level: CRITICAL**

Environment files should never be committed to git. The scanner detects .env files with actual secret values.

**Pattern:**

```bash
# .env file
API_KEY=sk-1234567890abcdef
DATABASE_URL=postgresql://user:password@localhost/db
```

**Detection Regex:**

```regex
^[A-Z_]+=\s*["\']?([a-zA-Z0-9_-]{20,})["\']?\s*$
```

**Note:** The scanner checks if the file being scanned is an actual .env file and flags any non-empty, non-comment lines with 20+ character values.

### 5. Third-Party Service Patterns

#### Firebase Configuration

**Risk Level: HIGH**

Firebase web apps include configuration objects with API keys. While Firebase keys are technically "public" (they're meant to be exposed), they should be loaded from environment variables in production.

**Pattern:**

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyD1234567890abcdef",
  authDomain: "app.firebaseapp.com",
  projectId: "app-123"
};
```

**Detection Regex:**

```regex
firebaseConfig\s*=\s*{[^}]*apiKey\s*:\s*["\']([a-zA-Z0-9_-]{20,})["\']
```

**Key indicators:**
- Variable name: `firebaseConfig`
- Contains `apiKey` property
- Google API key format: `AIza...`

#### Google Analytics Measurement IDs

**Risk Level: LOW**

Google Analytics IDs are public identifiers, not secrets. However, they should be documented and tracked.

**Pattern:**

```javascript
gtag('config', 'G-XXXXXXXXXX');
```

**Detection Regex:**

```regex
\bG-[A-Z0-9]{10}\b
```

**Note:** Uses word boundaries (`\b`) to avoid matching CSS classes like `bg-background`. These are generally safe to expose but should be loaded from environment variables for consistency.

#### API Endpoints with Embedded Keys

**Risk Level: HIGH**

API calls with keys embedded in URL parameters instead of headers.

**Pattern:**

```javascript
fetch('https://api.service.io/endpoint?api_key=sk-1234567890abcdef')
```

**Detection Regex:**

```regex
https?://[^\s"\']*api[_-]?key[_-]?=?[a-zA-Z0-9_-]{20,}
```

**Key indicators:**
- URL with `api_key=` or `apikey=` parameter
- 20+ character alphanumeric value

## Matching Mode

The scanner applies patterns **line by line**, not against entire file content. Each line is tested against all compiled patterns using `re.finditer()` with `re.IGNORECASE`. Anchors like `^` and `$` in patterns (e.g., the `.env` variable pattern) are evaluated relative to each individual line.

For the canonical source of truth, refer to the pattern definitions in `apps/backend/security/scan_secrets.py` (`FRONTEND_PATTERNS`, `GENERIC_PATTERNS`, etc.). This document mirrors those implementations and should be updated whenever the code changes.

## Testing Guidelines

### Creating Test Cases

When creating test cases for frontend patterns:

1. **Create realistic frontend code samples:**
   - TypeScript files for Electron/Vite apps
   - JSX/TSX files for React components
   - Plain JavaScript files

2. **Test both positive and negative cases:**
   - Positive: Hardcoded secrets that should be detected
   - Negative: Legitimate env variable usage that should NOT be detected

3. **Use fake secret builders** to avoid triggering push protection:

```python
# Build test secrets via concatenation
_TEST_OPENAI_KEY = "sk-" + "1234567890abcdefghijklmnop"
_TEST_GOOGLE_KEY = "AIza" + "012345678901234567890123456789012345"
```

4. **Example test cases:**

```javascript
// Should be detected
localStorage.setItem('apiKey', 'sk-12345678901234567890');

// Should NOT be detected (false positive - safe env usage)
const apiKey = import.meta.env.VITE_API_KEY;

// Should be detected
window.config = {
  apiKey: 'sk-12345678901234567890'
};

// Should NOT be detected (safe process.env reference)
const dsn = process.env.SENTRY_DSN;
```

## Implementation Notes

### Order of Pattern Matching

Frontend patterns are checked BEFORE generic patterns to provide more specific error messages. The current order in `ALL_PATTERNS` is:

1. FRONTEND_PATTERNS (most specific)
2. GENERIC_PATTERNS (catch-all)
3. SERVICE_PATTERNS (known formats)
4. PRIVATE_KEY_PATTERNS (cryptographic)
5. DATABASE_PATTERNS (connection strings)

### False Positive Filtering

Placeholder patterns use word boundaries or context-aware matching to avoid false negatives:
- `\bmock\b`, `\bfixture\b`, `\bdummy\b`, `\bfake\b` — word boundaries prevent matching inside identifiers
- `(?<![\w.-])example(?![\w.-])` — excludes domains like `api.example.com`
- `(?<![\w-])abc123(?![\w-])` — excludes token substrings separated by hyphens

### Cross-Platform Path Handling

The scanner normalizes file paths to POSIX format (forward slashes) before checking ignore patterns. This ensures Windows backslash paths (`C:\project\node_modules\...`) correctly match ignore rules like `node_modules/`.

### File Type Considerations

Frontend patterns currently apply to all scanned files. Future improvement could scope them to frontend file types:
- `.js`, `.jsx`, `.ts`, `.tsx` — JavaScript/TypeScript files
- `.vue` — Vue components
- `.svelte` — Svelte components
- `.env`, `.env.local`, `.env.production` — Environment files

### Framework-Specific Notes

**Vite:**
- Uses `import.meta.env` for build-time constants
- Build defines create `__VARIABLE__` globals
- Environment files: `.env`, `.env.local`, `.env.production`

**Create React App:**
- Uses `process.env` (injected by webpack)
- Environment files: `.env`, `.env.local`, `.env.production`

**Next.js:**
- Uses `process.env` for server-side
- Uses `import.meta.env` for client-side (Vite-based)
- Environment files: `.env.local`, `.env.development`

**Electron:**
- Main process: `process.env` (Node.js)
- Renderer: `import.meta.env` (Vite)
- Preload: `process.env` (Node.js context)

## References

### Common Frontend Secret Leaks

1. **localStorage/sessionStorage with hardcoded tokens**
   - Often happens during prototyping
   - Developers forget to remove before commit

2. **window.config in index.html**
   - Inline scripts with configuration
   - Should use template variables instead

3. **.env files committed to git**
   - `.env` should be in `.gitignore`
   - Only `.env.example` should be committed

4. **API endpoints with embedded keys**
   - URL parameters instead of headers
   - Keys visible in browser history/logs

### Related Security Issues

- **Hardcoded credentials in bundle:** Even if secrets are removed from source, they may remain in built bundles
- **Debug logging:** `console.log(apiKey)` statements expose secrets in browser console
- **Error messages:** Stack traces may include sensitive URLs with keys

## Additional Patterns to Consider

These patterns are not currently implemented but could be added in the future:

1. **Axios/Fetch interceptors with hardcoded auth:**

   ```javascript
   axios.interceptors.request.use(config => {
     config.headers.Authorization = 'Bearer sk-1234...';  // Hardcoded token
     return config;
   });
   ```

2. **React Context with secrets:**

   ```javascript
   const AuthContext = createContext({
     apiKey: 'sk-1234...'  // Direct value
   });
   ```

3. **Vue/Vuex stores with secrets:**

   ```javascript
   export default new Vuex.Store({
     state: {
       apiKey: 'sk-1234...'  // Hardcoded
     }
   });
   ```

4. **GraphQL clients with hardcoded tokens:**

   ```javascript
   const client = new ApolloClient({
     uri: 'https://api.service.io/graphql',
     headers: { 'Authorization': 'Bearer sk-1234...' }  // Hardcoded
   });
   ```

5. **Service Worker registration with tokens:**

   ```javascript
   navigator.serviceWorker.register('/sw.js?token=sk-1234...');  // Token in URL
   ```

## Summary

Frontend secret detection requires understanding the unique patterns used in web applications. The key challenge is balancing security (detecting real leaks) with usability (avoiding false positives for legitimate env variable usage).

The patterns documented here focus on:
- High-risk storage APIs (localStorage/sessionStorage)
- Common configuration patterns (window.config)
- Framework-specific env access (import.meta.env, process.env)
- Third-party service configs (Firebase, Google Analytics)
- Embedded secrets in API endpoints

All patterns follow the existing `scan_secrets.py` convention of tuple pairs: `(regex_pattern, description)`.
