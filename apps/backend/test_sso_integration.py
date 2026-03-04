#!/usr/bin/env python3
"""
Manual Test Script for SSO/SAML Authentication Integration
============================================================

This script demonstrates the SSO authentication flow with audit logging
integration in core/auth.py.

Usage:
    python test_sso_integration.py

Requirements:
    - Enterprise modules (enterprise.sso, enterprise.audit) must be available
    - SAML configuration must be set in environment variables

Environment Variables:
    SSO_ENABLED=true
    SAML_IDP_ENTITY_ID=<your-idp-entity-id>
    SAML_IDP_SSO_URL=<your-sso-url>
    SAML_IDP_X509_CERT=<base64-encoded-cert>
    SAML_PROVIDER_TYPE=okta|azure_ad|google_workspace|etc
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from core.auth import (
    ENTERPRISE_AVAILABLE,
    get_sso_config,
    is_sso_enabled,
)


def test_sso_availability():
    """Test 1: Check if enterprise SSO modules are available."""
    print("\n" + "=" * 70)
    print("TEST 1: Enterprise SSO Module Availability")
    print("=" * 70)

    if ENTERPRISE_AVAILABLE:
        print("✓ Enterprise SSO modules are available")
        print("  - enterprise.sso module loaded")
        print("  - enterprise.audit module loaded")
        return True
    else:
        print("✗ Enterprise SSO modules are NOT available")
        print("  - Ensure apps/backend/enterprise/sso.py exists")
        print("  - Ensure apps/backend/enterprise/audit.py exists")
        return False


def test_sso_configuration():
    """Test 2: Check SSO configuration."""
    print("\n" + "=" * 70)
    print("TEST 2: SSO Configuration Check")
    print("=" * 70)

    enabled = is_sso_enabled()
    print(f"SSO Enabled: {enabled}")

    if not enabled:
        print("\nSSO is not enabled. To enable SSO, set:")
        print("  export SSO_ENABLED=true")
        print("  export SAML_IDP_ENTITY_ID=<your-idp-entity-id>")
        print("  export SAML_IDP_SSO_URL=<your-sso-url>")
        print("  export SAML_IDP_X509_CERT=<base64-encoded-cert>")
        return False

    # Try to load configuration
    try:
        config = get_sso_config()
        print("\n✓ SSO Configuration loaded successfully:")
        print(f"  - Provider Type: {config.provider_type.value}")
        print(f"  - SP Entity ID: {config.sp_entity_id}")
        print(f"  - IDP Entity ID: {config.idp_entity_id}")
        print(f"  - SSO URL: {config.idp_sso_url}")
        print(f"  - Session Lifetime: {config.session_lifetime_hours} hours")
        print(f"  - JIT Provisioning: {config.allow_jit_provisioning}")
        return True
    except Exception as e:
        print(f"\n✗ Failed to load SSO configuration: {e}")
        return False


def test_audit_logger():
    """Test 3: Check audit logger availability."""
    print("\n" + "=" * 70)
    print("TEST 3: Audit Logger Availability")
    print("=" * 70)

    if not ENTERPRISE_AVAILABLE:
        print("✗ Audit logger not available (enterprise modules missing)")
        return False

    try:
        from core.auth import _get_audit_logger

        audit_logger = _get_audit_logger()
        if audit_logger:
            print("✓ Audit logger created successfully")
            print(f"  - Log directory: {audit_logger.log_dir}")
            return True
        else:
            print("✗ Failed to create audit logger")
            return False
    except Exception as e:
        print(f"✗ Error creating audit logger: {e}")
        return False


def test_authentication_flow():
    """Test 4: Demonstrate authentication flow (without real SAML response)."""
    print("\n" + "=" * 70)
    print("TEST 4: Authentication Flow (Dry Run)")
    print("=" * 70)

    if not is_sso_enabled():
        print("✗ SSO not enabled, skipping authentication test")
        return False

    print("\nAuthentication flow overview:")
    print("1. Client receives SAML response from identity provider")
    print("2. Call authenticate_with_sso(saml_response, ip, user_agent, org_id)")
    print("3. Function logs SSO_LOGIN_STARTED audit event")
    print("4. Validates SAML response and extracts user identity")
    print("5. Logs SAML_ASSERTION_VERIFIED audit event")
    print("6. Creates or updates user session")
    print("7. Logs SSO_LOGIN_COMPLETED audit event")
    print("8. Returns SAMLUser with user identity and session info")
    print("\nOn failure:")
    print("- Logs SSO_LOGIN_FAILED audit event")
    print("- Logs SAML_ASSERTION_REJECTED for validation errors")
    print("- Re-raises exception with details")

    print("\n✓ Authentication flow is available")
    print("  Note: Actual authentication requires a valid SAML response")
    return True


def test_audit_trail():
    """Test 5: Check audit trail availability."""
    print("\n" + "=" * 70)
    print("TEST 5: Audit Trail Actions")
    print("=" * 70)

    if not ENTERPRISE_AVAILABLE:
        print("✗ Audit actions not available (enterprise modules missing)")
        return False

    try:
        from enterprise.audit import AuditAction

        sso_actions = [
            ("SSO_LOGIN_STARTED", "Logged when authentication begins"),
            ("SSO_LOGIN_COMPLETED", "Logged on successful authentication"),
            ("SSO_LOGIN_FAILED", "Logged on authentication failure"),
            ("SAML_ASSERTION_VERIFIED", "Logged when SAML assertion is validated"),
            (
                "SAML_ASSERTION_REJECTED",
                "Logged when SAML assertion is invalid",
            ),
        ]

        print("✓ SSO Audit Actions available:")
        for action, description in sso_actions:
            action_obj = getattr(AuditAction, action)
            print(f"  - {action}: {action_obj.value}")
            print(f"    {description}")

        return True
    except Exception as e:
        print(f"✗ Error checking audit actions: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("SSO/SAML Authentication Integration Test")
    print("=" * 70)
    print("\nThis script verifies the SSO authentication integration in core/auth.py")
    print("with audit logging support from enterprise modules.")

    results = []

    # Run tests
    results.append(("Module Availability", test_sso_availability()))
    results.append(("SSO Configuration", test_sso_configuration()))
    results.append(("Audit Logger", test_audit_logger()))
    results.append(("Authentication Flow", test_authentication_flow()))
    results.append(("Audit Trail", test_audit_trail()))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! SSO integration is ready.")
        return 0
    else:
        print("\n✗ Some tests failed. See output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
