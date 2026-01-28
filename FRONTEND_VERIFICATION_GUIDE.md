# Frontend Verification Guide
## Manual Verification: Frontend with Authenticated API

This guide provides step-by-step instructions to verify that the frontend still works correctly after adding authentication to all API endpoints.

---

## Prerequisites

### 1. Environment Setup

**Backend (.env):**
```bash
cd apps/web-backend
cp .env.example .env
# Edit .env if needed - default values work for local development
```

**Frontend (.env):**
```bash
cd apps/web-frontend
cp .env.example .env
# Ensure VITE_API_URL=http://localhost:8000 and VITE_WS_URL=ws://localhost:8000
```

### 2. Install Dependencies

**Backend:**
```bash
cd apps/web-backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd apps/web-frontend
npm install
```

---

## Verification Steps

### Step 1: Start Backend Server

```bash
cd apps/web-backend
python -m uvicorn main:app --reload --port 8000 --host 127.0.0.1
```

**Expected Output:**
```
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**Verify Backend Health:**
```bash
curl http://localhost:8000/health
```

**Expected:** `{"status":"healthy","timestamp":"..."}`

---

### Step 2: Start Frontend Server

Open a **new terminal** and run:

```bash
cd apps/web-frontend
npm run dev
```

**Expected Output:**
```
  VITE v5.x.x  ready in XXX ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

---

### Step 3: Open Frontend in Browser

1. Open browser and navigate to: **http://localhost:3000**

2. **Expected:** Welcome page or task list displays without errors

---

### Step 4: Verify Frontend Functionality

#### ✅ Checklist 1: Frontend Loads Without Errors

- [ ] Page renders correctly (no white screen)
- [ ] No network errors in browser DevTools Console (F12 → Console tab)
- [ ] No 401 Unauthorized errors in Console
- [ ] Frontend layout and styling appears correct

**How to Check Console:**
- Press `F12` to open Developer Tools
- Click on "Console" tab
- Look for errors (red text)
- **Expected:** No errors, or only minor warnings

---

#### ✅ Checklist 2: Task List Displays

- [ ] Task list view loads successfully
- [ ] Tasks are displayed (if any specs exist in `.auto-claude/specs/`)
- [ ] Task cards show spec name, status, and metadata
- [ ] Empty state displays correctly if no tasks exist

**How to Verify:**
- Navigate to task list (usually the home page)
- Look for task cards with spec information
- If no tasks exist, you should see an "No tasks found" or similar message

---

#### ✅ Checklist 3: Can View Task Details

- [ ] Click on a task card
- [ ] Task detail page loads
- [ ] Spec details display correctly (description, status, subtasks)
- [ ] Progress bar shows correct percentage
- [ ] No console errors when viewing details

**How to Verify:**
- Click on any task in the task list
- Verify the detail page loads with full spec information
- Check console for errors (F12 → Console)

---

#### ✅ Checklist 4: No Console Errors

Open browser DevTools (F12) and verify:

- [ ] **Console Tab:** No red error messages
- [ ] **Network Tab:** All API calls return 200 or expected status codes
- [ ] **Network Tab:** No failed requests (red status)
- [ ] **Console Tab:** No CORS errors

**Common Expected Warnings (OK to ignore):**
- React DevTools warnings
- Browser extension warnings
- Source map warnings

**Errors to Watch For (MUST FIX):**
- `401 Unauthorized` - Authentication not working
- `CORS policy` errors - Backend CORS not configured correctly
- `Failed to fetch` - Backend not running or wrong URL
- React rendering errors - Component bugs

---

#### ✅ Checklist 5: WebSocket Connects

- [ ] WebSocket connection established successfully
- [ ] Real-time updates work (if backend emits events)
- [ ] No WebSocket errors in console

**How to Verify WebSocket:**

1. Open DevTools (F12) → **Console** tab
2. Look for WebSocket connection logs (frontend should log connection status)
3. Open **Network** tab → filter by "WS" (WebSocket)
4. You should see a WebSocket connection to `ws://localhost:8000/ws`
5. Status should be "101 Switching Protocols" (successful handshake)

**Expected Console Logs:**
```
WebSocket connected: ws://localhost:8000/ws
WebSocket ready to receive real-time updates
```

**Check WebSocket Status in Network Tab:**
- DevTools → Network → WS filter
- Click on the WebSocket connection
- **Status:** 101 Switching Protocols
- **Type:** websocket
- **Frames tab:** Shows messages sent/received

---

## Troubleshooting

### Issue: Frontend shows 401 Unauthorized errors

**Cause:** API authentication not configured correctly

**Fix:**
1. Verify backend is using the correct JWT secret
2. Check that frontend is sending auth token (if implemented)
3. Review `apps/web-backend/core/security.py` for auth logic
4. Check browser Local Storage for auth token: `localStorage.getItem('auth_token')`

---

### Issue: CORS errors in console

**Error Message:**
```
Access to fetch at 'http://localhost:8000/api/tasks' from origin 'http://localhost:3000'
has been blocked by CORS policy
```

**Fix:**
1. Check backend `.env` file has correct CORS_ORIGINS:
   ```
   CORS_ORIGINS=http://localhost:3000,http://localhost:5173
   ```
2. Restart backend server after changing .env
3. Verify `main.py` includes CORS middleware

---

### Issue: WebSocket fails to connect

**Error:** `WebSocket connection failed` or `Error during WebSocket handshake`

**Fix:**
1. Verify backend WebSocket endpoint is running: `/ws`
2. Check that frontend is using correct WebSocket URL: `ws://localhost:8000/ws`
3. Review WebSocket authentication (if implemented)
4. Check backend logs for WebSocket errors

---

### Issue: Tasks don't load (empty list)

**Cause:** No specs exist in `.auto-claude/specs/` directory

**Not a Bug If:**
- You haven't created any specs yet
- This is a fresh installation

**How to Create Test Data:**
1. Create a test spec in `.auto-claude/specs/001-test-spec/`
2. Add a `spec.md` file with minimal content
3. Refresh frontend - task should appear

---

## Expected Test Results

### ✅ All Checks Pass

If all checklists above pass, the frontend is working correctly with the authenticated API.

**Sign-off Criteria Met:**
- ✅ Frontend loads without errors
- ✅ Task list displays
- ✅ Can view task details
- ✅ No console errors
- ✅ WebSocket connects

---

### ❌ Some Checks Fail

If any checklist items fail, document the failures and fix before marking subtask complete.

**Common Issues:**
1. **401 Errors:** Authentication implementation issue - review auth dependency injection
2. **CORS Errors:** Backend CORS configuration issue - check `CORS_ORIGINS` in .env
3. **WebSocket Errors:** WebSocket endpoint issue - verify `/ws` route exists
4. **Network Errors:** Backend not running - start backend server
5. **React Errors:** Frontend component bugs - check component code

---

## API Authentication Verification

To verify authentication is working correctly, you can also test API endpoints directly:

### Test 1: Health Endpoint (No Auth Required)
```bash
curl -i http://localhost:8000/health
```
**Expected:** `200 OK` with `{"status":"healthy"}`

### Test 2: Tasks Endpoint (Auth Required)
```bash
curl -i http://localhost:8000/api/tasks
```
**Expected:** `401 Unauthorized` with `{"detail":"Not authenticated"}`

### Test 3: Get Valid Token
```bash
curl -X POST http://localhost:8000/api/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"token":"test-token"}'
```
**Expected:** Returns a valid JWT token (or 401 if token invalid)

### Test 4: Access with Valid Token
```bash
# First, get a valid token from /api/auth/verify
TOKEN="<your-token-here>"

curl -i -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/tasks
```
**Expected:** `200 OK` with task list JSON

---

## Automated Test Verification

The frontend has comprehensive test coverage that can be run to verify functionality:

### Unit Tests (Vitest)
```bash
cd apps/web-frontend
npm test
```
**Expected:** 143 tests pass, 91.71% coverage

### E2E Tests (Playwright)
```bash
cd apps/web-frontend
npm run test:e2e
```
**Expected:** 73 tests pass (task-list, navigation, real-time-updates)

---

## Summary

This manual verification ensures that:

1. **Authentication is transparent to the user** - Frontend handles auth tokens automatically
2. **No regressions** - All existing functionality still works
3. **API security** - Backend enforces authentication on all protected endpoints
4. **Real-time updates** - WebSocket connection works with authentication
5. **Error handling** - Graceful handling of auth failures and errors

**If all checks pass, the frontend successfully works with the authenticated API!**

---

## Notes

- **Environment Compatibility:** This guide assumes Python 3.12 or 3.13 (PyO3 compatibility)
- **Development Only:** Uses dev JWT secret - change in production
- **Token Storage:** Frontend may store tokens in localStorage or sessionStorage
- **Auto-Refresh:** Frontend should automatically refresh page on 401 errors (if implemented)

---

## Related Documents

- Backend verification: `MANUAL_VERIFICATION.md`
- QA report: `.auto-claude/specs/022-web-interface-browser-based-access/qa_report.md`
- Spec: `.auto-claude/specs/040-qa-validation-complete/spec.md`
