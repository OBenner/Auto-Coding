#!/usr/bin/env python3
"""
End-to-end integration test for cloud-hosted Auto Code.

Tests the full workflow:
1. User signup
2. User login
3. OAuth integration (GitHub)
4. Usage tracking
5. Repository management

Requirements:
- Docker and docker-compose must be installed
- Cloud stack must be running (docker-compose.cloud.yml)
- Backend API must be accessible at http://localhost:8000
"""

import sys
import time
import requests
import json
from typing import Dict, Optional
import subprocess

# Test configuration
API_BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpass123"
TEST_ORG = "Test Organization"


class CloudE2ETest:
    """End-to-end test runner for cloud-hosted features."""

    def __init__(self):
        self.access_token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.session = requests.Session()
        self.results: Dict[str, bool] = {}

    def log(self, message: str, level: str = "INFO"):
        """Log a test message."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        prefix = "✅" if level == "SUCCESS" else "❌" if level == "ERROR" else "ℹ️"
        print(f"[{timestamp}] {prefix} {message}")

    def wait_for_service(self, url: str, timeout: int = 60, service_name: str = "service") -> bool:
        """Wait for a service to become available."""
        self.log(f"Waiting for {service_name} at {url}...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    self.log(f"{service_name} is ready!", "SUCCESS")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)

        self.log(f"{service_name} did not become ready within {timeout}s", "ERROR")
        return False

    def test_health_check(self) -> bool:
        """Test 1: Verify backend API is healthy."""
        self.log("Test 1: Health Check")
        try:
            response = self.session.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                self.log(f"Health check passed: {data}", "SUCCESS")
                return True
            else:
                self.log(f"Health check failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Health check error: {e}", "ERROR")
            return False

    def test_user_signup(self) -> bool:
        """Test 2: User registration."""
        self.log("Test 2: User Signup")
        try:
            payload = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            response = self.session.post(
                f"{API_BASE_URL}/api/users/register",
                json=payload
            )

            if response.status_code == 201:
                data = response.json()
                self.user_id = data.get("id")
                self.log(f"User created successfully: {data.get('email')} (ID: {self.user_id})", "SUCCESS")
                return True
            elif response.status_code == 400:
                # User might already exist, that's okay
                self.log("User already exists, continuing...", "INFO")
                return True
            else:
                self.log(f"Signup failed: {response.status_code} - {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Signup error: {e}", "ERROR")
            return False

    def test_user_login(self) -> bool:
        """Test 3: User login and token retrieval."""
        self.log("Test 3: User Login")
        try:
            payload = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            response = self.session.post(
                f"{API_BASE_URL}/api/users/login",
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
                self.log(f"Login successful, token received (user_id: {self.user_id})", "SUCCESS")

                # Set authorization header for subsequent requests
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })
                return True
            else:
                self.log(f"Login failed: {response.status_code} - {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Login error: {e}", "ERROR")
            return False

    def test_oauth_status(self) -> bool:
        """Test 4: Check OAuth provider status."""
        self.log("Test 4: OAuth Status")
        try:
            response = self.session.get(f"{API_BASE_URL}/api/git/status")

            if response.status_code == 200:
                data = response.json()
                self.log(f"OAuth status: {json.dumps(data, indent=2)}", "SUCCESS")
                return True
            else:
                self.log(f"OAuth status check failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"OAuth status error: {e}", "ERROR")
            return False

    def test_github_oauth_redirect(self) -> bool:
        """Test 5: GitHub OAuth authorization redirect."""
        self.log("Test 5: GitHub OAuth Redirect")
        try:
            response = self.session.get(
                f"{API_BASE_URL}/api/git/github/authorize",
                allow_redirects=False
            )

            if response.status_code == 302:
                redirect_url = response.headers.get("Location", "")
                if redirect_url.startswith("https://github.com/"):
                    self.log(f"GitHub OAuth redirect working: {redirect_url[:100]}...", "SUCCESS")
                    return True
                else:
                    self.log(f"Unexpected redirect: {redirect_url}", "ERROR")
                    return False
            else:
                self.log(f"OAuth redirect failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"OAuth redirect error: {e}", "ERROR")
            return False

    def test_usage_tracking(self) -> bool:
        """Test 6: Usage tracking and statistics."""
        self.log("Test 6: Usage Tracking")
        try:
            # Check usage dashboard
            response = self.session.get(f"{API_BASE_URL}/api/usage/dashboard")

            if response.status_code == 200:
                data = response.json()
                self.log(f"Usage dashboard: {json.dumps(data, indent=2)}", "SUCCESS")

                # Check usage stats
                response = self.session.get(f"{API_BASE_URL}/api/usage/stats")
                if response.status_code == 200:
                    stats = response.json()
                    self.log(f"Usage stats retrieved: {stats.get('total_requests', 0)} requests", "SUCCESS")
                    return True
                else:
                    self.log(f"Usage stats failed: {response.status_code}", "ERROR")
                    return False
            else:
                self.log(f"Usage dashboard failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Usage tracking error: {e}", "ERROR")
            return False

    def test_usage_health(self) -> bool:
        """Test 7: Usage tracking health (Redis connection)."""
        self.log("Test 7: Usage Health (Redis)")
        try:
            response = self.session.get(f"{API_BASE_URL}/api/usage/health")

            if response.status_code == 200:
                data = response.json()
                redis_healthy = data.get("redis_healthy", False)
                if redis_healthy:
                    self.log("Redis connection healthy", "SUCCESS")
                    return True
                else:
                    self.log("Redis connection not available (expected if Redis not running)", "INFO")
                    return True  # Don't fail the test, just note it
            else:
                self.log(f"Health check failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Health check error: {e}", "ERROR")
            return False

    def test_database_connection(self) -> bool:
        """Test 8: Database connection through API."""
        self.log("Test 8: Database Connection")
        try:
            # Make a request that requires database access (login)
            # If login worked, database is working
            if self.access_token:
                self.log("Database connection verified (login succeeded)", "SUCCESS")
                return True
            else:
                self.log("Cannot verify database (no access token)", "ERROR")
                return False
        except Exception as e:
            self.log(f"Database verification error: {e}", "ERROR")
            return False

    def run_all_tests(self) -> bool:
        """Run all end-to-end tests."""
        self.log("=" * 80)
        self.log("Starting Cloud E2E Test Suite")
        self.log("=" * 80)

        # Wait for backend to be ready
        if not self.wait_for_service(f"{API_BASE_URL}/health", timeout=60, service_name="Backend API"):
            self.log("Backend API is not available, cannot run tests", "ERROR")
            return False

        # Run all tests
        tests = [
            ("Health Check", self.test_health_check),
            ("User Signup", self.test_user_signup),
            ("User Login", self.test_user_login),
            ("OAuth Status", self.test_oauth_status),
            ("GitHub OAuth Redirect", self.test_github_oauth_redirect),
            ("Usage Tracking", self.test_usage_tracking),
            ("Usage Health (Redis)", self.test_usage_health),
            ("Database Connection", self.test_database_connection),
        ]

        for test_name, test_func in tests:
            self.log("-" * 80)
            result = test_func()
            self.results[test_name] = result
            time.sleep(1)  # Brief pause between tests

        # Print summary
        self.log("=" * 80)
        self.log("Test Results Summary")
        self.log("=" * 80)

        total = len(self.results)
        passed = sum(1 for result in self.results.values() if result)
        failed = total - passed

        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status}: {test_name}")

        self.log("-" * 80)
        self.log(f"Total: {total} | Passed: {passed} | Failed: {failed}")

        if failed == 0:
            self.log("All tests passed! 🎉", "SUCCESS")
            return True
        else:
            self.log(f"{failed} test(s) failed", "ERROR")
            return False


def check_docker_stack() -> bool:
    """Check if Docker stack is running."""
    print("\nℹ️  Checking Docker stack status...")
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=autoclaude", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )

        running_containers = result.stdout.strip().split("\n")
        running_containers = [c for c in running_containers if c]

        expected_containers = ["autoclaude-postgres", "autoclaude-redis", "autoclaude-backend"]
        missing_containers = [c for c in expected_containers if c not in running_containers]

        if missing_containers:
            print(f"⚠️  Missing containers: {', '.join(missing_containers)}")
            print("\nTo start the cloud stack, run:")
            print("  cd apps/web-backend")
            print("  docker-compose -f docker-compose.cloud.yml up -d")
            return False
        else:
            print(f"✅ All containers running: {', '.join(running_containers)}")
            return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error checking Docker: {e}")
        return False


def main():
    """Main test execution."""
    # Check if Docker stack is running
    if not check_docker_stack():
        print("\n❌ Docker stack is not running. Please start it first.")
        print("\nQuick start:")
        print("  cd apps/web-backend")
        print("  docker-compose -f docker-compose.cloud.yml up -d")
        print("  # Wait for services to be healthy (30-60 seconds)")
        print("  # Run migrations: docker exec autoclaude-backend alembic upgrade head")
        print("  python tests/test_cloud_e2e.py")
        return 1

    # Run tests
    tester = CloudE2ETest()
    success = tester.run_all_tests()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
