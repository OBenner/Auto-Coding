"""
Language Security Rules
=======================

Security scanners and validation rules for different programming languages.
Defines language-specific security tools and common security patterns.
"""

# =============================================================================
# LANGUAGE SECURITY SCANNERS
# =============================================================================

# Security scanners for each language
# Maps language name to set of security scanner commands
LANGUAGE_SECURITY_SCANNERS: dict[str, set[str]] = {
    "go": {
        "gosec",  # Go security checker
        "staticcheck",  # Go static analysis
        "govulncheck",  # Go vulnerability scanner
    },
    "rust": {
        "cargo-audit",  # Rust dependency vulnerability scanner
        "cargo-deny",  # Rust dependency checker for licenses/security
        "cargo-clippy",  # Rust linter (includes security checks)
    },
    "php": {
        "phpstan",  # PHP static analysis
        "psalm",  # PHP static analysis and security scanner
        "phpcs",  # PHP CodeSniffer
        "security-checker",  # Symfony security checker
    },
    "ruby": {
        "brakeman",  # Ruby on Rails security scanner
        "bundler-audit",  # Ruby dependency vulnerability scanner
        "rubocop",  # Ruby linter (includes security cops)
    },
    "python": {
        "bandit",  # Python security linter
        "safety",  # Python dependency vulnerability scanner
        "semgrep",  # Multi-language security scanner
    },
    "javascript": {
        "eslint",  # JavaScript linter (with security plugins)
        "npm-audit",  # npm dependency vulnerability scanner
        "semgrep",  # Multi-language security scanner
    },
    "typescript": {
        "eslint",  # TypeScript linter (with security plugins)
        "npm-audit",  # npm dependency vulnerability scanner
        "semgrep",  # Multi-language security scanner
    },
}


# =============================================================================
# LANGUAGE SECURITY RULES
# =============================================================================

# Common security anti-patterns and dangerous functions for each language
LANGUAGE_SECURITY_RULES: dict[str, dict[str, list[str]]] = {
    "go": {
        "dangerous_functions": [
            "exec.Command",  # Command injection risk
            "syscall.Exec",  # Command injection risk
            "template.HTML",  # XSS risk if not sanitized
            "sql.Query",  # SQL injection risk without parameterization
            "ioutil.ReadFile",  # Path traversal risk
            "http.Get",  # SSRF risk without validation
        ],
        "unsafe_patterns": [
            "crypto/md5",  # Weak hash algorithm
            "crypto/sha1",  # Weak hash algorithm
            "math/rand",  # Not cryptographically secure
            "unsafe.Pointer",  # Memory safety issues
        ],
        "secure_alternatives": [
            "Use crypto/rand for random numbers",
            "Use crypto/sha256 or crypto/sha512 for hashing",
            "Use prepared statements for SQL queries",
            "Validate and sanitize all user inputs",
        ],
    },
    "rust": {
        "dangerous_functions": [
            "std::process::Command",  # Command injection risk
            "std::fs::read",  # Path traversal risk
            "reqwest::get",  # SSRF risk without validation
            "unsafe",  # Memory safety bypass
        ],
        "unsafe_patterns": [
            "unwrap()",  # Panic on None/Err
            "expect()",  # Panic on None/Err
            "transmute",  # Type safety bypass
            "as *const",  # Raw pointer conversion
        ],
        "secure_alternatives": [
            "Use Result/Option pattern instead of unwrap()",
            "Use safe abstractions instead of unsafe blocks",
            "Validate file paths before reading",
            "Use URL validation before making requests",
        ],
    },
    "php": {
        "dangerous_functions": [
            "eval",  # Code injection
            "exec",  # Command injection
            "system",  # Command injection
            "shell_exec",  # Command injection
            "passthru",  # Command injection
            "unserialize",  # Object injection
            "file_get_contents",  # SSRF/LFI risk
            "include",  # LFI/RFI risk
            "require",  # LFI/RFI risk
        ],
        "unsafe_patterns": [
            "mysql_query",  # Use PDO instead
            "md5",  # Weak hash for passwords
            "sha1",  # Weak hash for passwords
            "extract",  # Variable overwriting
            "$_GET",  # Unvalidated input
            "$_POST",  # Unvalidated input
            "$_REQUEST",  # Unvalidated input
        ],
        "secure_alternatives": [
            "Use PDO with prepared statements for database queries",
            "Use password_hash() and password_verify() for passwords",
            "Validate and sanitize all user inputs",
            "Use htmlspecialchars() to prevent XSS",
            "Avoid eval() and other code execution functions",
        ],
    },
    "ruby": {
        "dangerous_functions": [
            "eval",  # Code injection
            "system",  # Command injection
            "exec",  # Command injection
            "backticks",  # Command injection (`)
            "Kernel.open",  # Command injection risk
            "YAML.load",  # Deserialization vulnerability
            "Marshal.load",  # Deserialization vulnerability
        ],
        "unsafe_patterns": [
            "send(:method_name)",  # Arbitrary method execution
            "const_get",  # Arbitrary constant access
            "instance_variable_get",  # Bypasses encapsulation
            "File.read",  # Path traversal risk
            "params[:key]",  # Mass assignment vulnerability
        ],
        "secure_alternatives": [
            "Use YAML.safe_load instead of YAML.load",
            "Use strong_parameters in Rails for mass assignment",
            "Validate and sanitize all user inputs",
            "Use parameterized queries for database operations",
            "Avoid dynamic method calls with user input",
        ],
    },
    "python": {
        "dangerous_functions": [
            "eval",  # Code injection
            "exec",  # Code injection
            "compile",  # Code injection
            "os.system",  # Command injection
            "subprocess.call",  # Command injection without shell=False
            "pickle.loads",  # Deserialization vulnerability
            "yaml.load",  # Deserialization vulnerability
        ],
        "unsafe_patterns": [
            "shell=True",  # Command injection risk in subprocess
            "assert",  # Removed in optimized mode
            "input",  # Can execute code in Python 2
            "md5",  # Weak hash for passwords
            "random.random",  # Not cryptographically secure
        ],
        "secure_alternatives": [
            "Use yaml.safe_load instead of yaml.load",
            "Use subprocess with shell=False and list arguments",
            "Use secrets module for cryptographically secure random",
            "Use hashlib.pbkdf2_hmac or bcrypt for password hashing",
            "Validate and sanitize all user inputs",
        ],
    },
    "javascript": {
        "dangerous_functions": [
            "eval",  # Code injection
            "Function",  # Code injection
            "setTimeout",  # Code injection with string argument
            "setInterval",  # Code injection with string argument
            "document.write",  # XSS risk
            "innerHTML",  # XSS risk
            "exec",  # Command injection (Node.js)
        ],
        "unsafe_patterns": [
            "dangerouslySetInnerHTML",  # XSS risk in React
            "v-html",  # XSS risk in Vue
            "Math.random",  # Not cryptographically secure
            "==",  # Type coercion issues
            "with",  # Scope confusion
        ],
        "secure_alternatives": [
            "Use crypto.randomBytes for secure random numbers",
            "Use textContent instead of innerHTML",
            "Use === for comparisons",
            "Validate and sanitize all user inputs",
            "Use Content Security Policy (CSP) headers",
        ],
    },
    "typescript": {
        "dangerous_functions": [
            "eval",  # Code injection
            "Function",  # Code injection
            "setTimeout",  # Code injection with string argument
            "setInterval",  # Code injection with string argument
            "innerHTML",  # XSS risk
            "exec",  # Command injection (Node.js)
        ],
        "unsafe_patterns": [
            "any",  # Bypasses type safety
            "as any",  # Type assertion bypass
            "dangerouslySetInnerHTML",  # XSS risk in React
            "Math.random",  # Not cryptographically secure
            "==",  # Type coercion issues
        ],
        "secure_alternatives": [
            "Use unknown instead of any for better type safety",
            "Use crypto.randomBytes for secure random numbers",
            "Use textContent instead of innerHTML",
            "Use === for comparisons",
            "Validate and sanitize all user inputs",
        ],
    },
}


__all__ = ["LANGUAGE_SECURITY_SCANNERS", "LANGUAGE_SECURITY_RULES"]
