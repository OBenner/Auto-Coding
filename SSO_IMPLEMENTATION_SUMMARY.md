# SSO Token Validation and User Identity Mapping Implementation

## Summary
Enhanced the `enterprise/sso.py` module with robust token validation and user identity mapping functions, following patterns from `core/auth.py`.

## New Functions Added

### 1. `is_valid_saml_token_format(token: str | None) -> bool`
- Validates SAML token format (base64-encoded XML)
- Checks token length, base64 encoding, and XML structure
- Returns boolean indicating validity
- Pattern: Similar to `is_encrypted_token()` in `core/auth.py`

### 2. `validate_saml_token_format(token: str) -> None`
- Comprehensive format validation with detailed error messages
- Validates:
  - Token is not empty/None
  - Token is a string
  - Token has minimum length (100+ chars)
  - Token is valid base64
  - Decoded content is XML
- Pattern: Similar to `validate_token_not_encrypted()` in `core/auth.py`
- Raises `ValueError` with helpful troubleshooting guidance

### 3. `map_saml_attributes(assertion: SAMLAssertion, attribute_map: dict) -> dict`
- Maps SAML assertion attributes to application attributes
- Uses configured attribute mapping from SAMLConfig
- Returns dictionary with app-friendly keys
- Example: Maps long SAML URIs to simple keys like "email", "first_name"

### 4. `create_user_from_saml(assertion: SAMLAssertion, attribute_map: dict, organization_id: str | None) -> SAMLUser`
- Creates SAMLUser from validated assertion
- Handles attribute mapping and extraction
- Validates required fields (email)
- Normalizes group memberships to list format
- Includes proper logging

### 5. Enhanced `validate_saml_token(saml_response: str, config: SAMLConfig) -> SAMLUser`
- **Main entry point** for SAML token validation
- Added pre-validation of token format
- Enhanced error handling and logging
- Better error messages with troubleshooting steps
- Follows validation pattern from `core/auth.py`

## Key Improvements

1. **Better Error Messages**: All validation failures provide:
   - Clear explanation of what went wrong
   - Possible causes
   - Steps to fix the issue

2. **Robust Validation**: Multiple validation layers:
   - Format validation (base64, XML)
   - Length validation
   - Content validation
   - SAML spec compliance (issuer, expiration, audience)

3. **Logging**: Comprehensive logging at appropriate levels:
   - Debug: Validation checkpoints
   - Info: Successful operations
   - Error: Failures with context

4. **Pattern Consistency**: Follows established patterns from `core/auth.py`:
   - Validation helper functions
   - Clear error messages with troubleshooting
   - Proper exception handling
   - Logging conventions

## Integration Points

The enhanced validation integrates with existing SAMLProvider functionality:
- Used by `SAMLProvider.validate_response()`
- Compatible with all supported IDPs (Okta, Azure AD, Google, OneLogin, Auth0)
- Works with JIT provisioning
- Supports attribute mapping configuration

## Testing Notes

Functions are designed for:
- Unit testing with mock SAML responses
- Integration testing with real IDP responses
- Error case testing with invalid tokens

The implementation is syntactically valid and follows Python 3.11+ requirements (matching existing codebase standards).
