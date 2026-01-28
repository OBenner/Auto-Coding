@echo off
REM Authentication Verification Script for Auto Claude Web Backend (Windows)
REM This script verifies that API authentication is working correctly

echo ==========================================
echo Auto Claude Web Backend Authentication Verification
echo ==========================================
echo.

REM Check if server is running
echo Step 1: Checking if server is running on http://localhost:8000...
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo X Server is NOT running
    echo.
    echo Please start the server first:
    echo   cd apps\web-backend
    echo   python -m uvicorn main:app --host localhost --port 8000
    exit /b 1
)
echo + Server is running
echo.

REM Test 1: Request without authentication should return 401
echo Test 1: Request without authentication (should return 401)...
curl -s -o response.tmp -w "%%{http_code}" http://localhost:8000/api/tasks > http_code.tmp
set /p HTTP_CODE=<http_code.tmp
if "%HTTP_CODE%"=="401" (
    echo + Test 1 PASSED: Got 401 Unauthorized as expected
) else (
    echo X Test 1 FAILED: Expected 401, got %HTTP_CODE%
    type response.tmp
)
echo.

REM Test 2: Request with invalid token should return 401
echo Test 2: Request with invalid token (should return 401)...
curl -s -o response.tmp -w "%%{http_code}" -H "Authorization: Bearer invalid" http://localhost:8000/api/tasks > http_code.tmp
set /p HTTP_CODE=<http_code.tmp
if "%HTTP_CODE%"=="401" (
    echo + Test 2 PASSED: Got 401 Unauthorized for invalid token
) else (
    echo X Test 2 FAILED: Expected 401, got %HTTP_CODE%
    type response.tmp
)
echo.

REM Test 3: Get valid token from /api/auth/verify
echo Test 3: Getting valid token from /api/auth/verify...
curl -s http://localhost:8000/api/auth/verify > token_response.tmp
REM Parse JSON to extract token (requires Python)
python -c "import json; data=json.load(open('token_response.tmp')); print(data['token'])" > token.tmp 2>nul
set /p TOKEN=<token.tmp
if "%TOKEN%"=="" (
    echo X Test 3 FAILED: Could not extract token from response
    type token_response.tmp
    exit /b 1
)
echo + Test 3 PASSED: Successfully obtained token
echo Token (first 20 chars): %TOKEN:~0,20%...
echo.

REM Test 4: Request with valid token should return 200
echo Test 4: Request with valid token (should return 200)...
curl -s -o response.tmp -w "%%{http_code}" -H "Authorization: Bearer %TOKEN%" http://localhost:8000/api/tasks > http_code.tmp
set /p HTTP_CODE=<http_code.tmp
if "%HTTP_CODE%"=="200" (
    echo + Test 4 PASSED: Got 200 OK with valid token
) else (
    echo X Test 4 FAILED: Expected 200, got %HTTP_CODE%
    type response.tmp
)
echo.

REM Additional Test: Verify /api/specs endpoint also requires auth
echo Additional Test 5: /api/specs without auth (should return 401)...
curl -s -o response.tmp -w "%%{http_code}" http://localhost:8000/api/specs > http_code.tmp
set /p HTTP_CODE=<http_code.tmp
if "%HTTP_CODE%"=="401" (
    echo + Test 5 PASSED: /api/specs requires authentication
) else (
    echo X Test 5 FAILED: Expected 401, got %HTTP_CODE%
)
echo.

REM Additional Test: Verify /api/agents/run endpoint requires auth
echo Additional Test 6: /api/agents/run without auth (should return 401)...
curl -s -o response.tmp -w "%%{http_code}" -X POST http://localhost:8000/api/agents/run -H "Content-Type: application/json" -d "{}" > http_code.tmp
set /p HTTP_CODE=<http_code.tmp
if "%HTTP_CODE%"=="401" (
    echo + Test 6 PASSED: /api/agents/run requires authentication
) else (
    echo X Test 6 FAILED: Expected 401, got %HTTP_CODE%
)
echo.

REM Additional Test: Verify /health endpoint does NOT require auth
echo Additional Test 7: /health without auth (should return 200)...
curl -s -o response.tmp -w "%%{http_code}" http://localhost:8000/health > http_code.tmp
set /p HTTP_CODE=<http_code.tmp
if "%HTTP_CODE%"=="200" (
    echo + Test 7 PASSED: /health endpoint is public
) else (
    echo X Test 7 FAILED: Expected 200, got %HTTP_CODE%
)
echo.

REM Cleanup
del response.tmp http_code.tmp token_response.tmp token.tmp 2>nul

echo ==========================================
echo Authentication Verification Complete
echo ==========================================
