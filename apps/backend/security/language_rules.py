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
    "c": {
        "cppcheck",  # C/C++ static analysis
        "clang-tidy",  # Clang-based linter (includes security checks)
        "flawfinder",  # C/C++ security weakness scanner
    },
    "cpp": {
        "cppcheck",  # C/C++ static analysis
        "clang-tidy",  # Clang-based linter (includes security checks)
        "flawfinder",  # C/C++ security weakness scanner
    },
    "java": {
        "spotbugs",  # Java bytecode static analysis (with find-sec-bugs)
        "semgrep",  # Multi-language security scanner
        "osv-scanner",  # Known-vulnerability scanner for Maven/Gradle deps
    },
    "kotlin": {
        "detekt",  # Kotlin static analysis
        "semgrep",  # Multi-language security scanner
        "osv-scanner",  # Known-vulnerability scanner for Maven/Gradle deps
    },
    "csharp": {
        "security-scan",  # Security Code Scan for .NET
        "semgrep",  # Multi-language security scanner
        "osv-scanner",  # Known-vulnerability scanner for NuGet deps
    },
    "elixir": {
        "sobelow",  # Phoenix/Elixir security scanner
        "credo",  # Elixir static analysis
        "osv-scanner",  # Known-vulnerability scanner for Hex deps
    },
    "swift": {
        "swiftlint",  # Swift linter
        "osv-scanner",  # Known-vulnerability scanner for SwiftPM deps
    },
    "scala": {
        "scalafix",  # Scala linter/refactoring tool
        "semgrep",  # Multi-language security scanner
        "osv-scanner",  # Known-vulnerability scanner for sbt/Maven deps
    },
    "dart": {
        "dart-analyze",  # Dart static analysis (dart analyze)
        "osv-scanner",  # Known-vulnerability scanner for pub deps
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
            "os.ReadFile",  # Path traversal risk (formerly ioutil.ReadFile, deprecated since Go 1.16)
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
    "c": {
        "dangerous_functions": [
            "gets",  # No bounds checking, always an overflow
            "strcpy",  # Unbounded copy
            "strcat",  # Unbounded concatenation
            "sprintf",  # Unbounded format write
            "vsprintf",  # Unbounded format write
            "scanf",  # %s without width specifier overflows
            "system",  # Command injection
            "popen",  # Command injection
            "tmpnam",  # Race condition (TOCTOU)
        ],
        "unsafe_patterns": [
            "malloc",  # Result must be NULL-checked
            "alloca",  # Stack overflow risk with variable sizes
            "memcpy",  # Size argument must be validated
            "printf(",  # Format string vulnerability if user-controlled
        ],
        "secure_alternatives": [
            "Use fgets/snprintf/strncat with explicit buffer sizes",
            "Use execv family with argument arrays instead of system()",
            "Check every allocation result before use",
            "Build and run tests with -fsanitize=address,undefined",
            "Run valgrind or AddressSanitizer to catch memory errors",
        ],
    },
    "cpp": {
        "dangerous_functions": [
            "gets",  # No bounds checking, always an overflow
            "strcpy",  # Unbounded copy
            "sprintf",  # Unbounded format write
            "system",  # Command injection
            "popen",  # Command injection
            "reinterpret_cast",  # Type safety bypass
            "const_cast",  # Constness bypass, often UB
        ],
        "unsafe_patterns": [
            "new ",  # Prefer smart pointers over raw new/delete
            "delete ",  # Manual lifetime management risk
            "c_str()",  # Dangling pointer if string is temporary
            "[i]",  # Unchecked indexing, prefer at() for user input
        ],
        "secure_alternatives": [
            "Use std::string/std::vector instead of raw buffers",
            "Use std::unique_ptr/std::shared_ptr instead of new/delete",
            "Use at() for bounds-checked access on untrusted indices",
            "Build and run tests with -fsanitize=address,undefined",
            "Run valgrind or AddressSanitizer to catch memory errors",
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
    "java": {
        "dangerous_functions": [
            "Runtime.exec",  # Command injection risk
            "ProcessBuilder",  # Command injection risk
            "ObjectInputStream",  # Deserialization vulnerability
            "XMLDecoder",  # Deserialization vulnerability
            "Class.forName",  # Reflection-based code loading
            "ScriptEngine.eval",  # Code injection
        ],
        "unsafe_patterns": [
            "createStatement",  # SQL injection, use PreparedStatement
            "DocumentBuilderFactory",  # XXE unless secure processing enabled
            "TrustAllCerts",  # Disabled TLS validation
            "MD5",  # Weak hash algorithm
            "SHA1",  # Weak hash algorithm
        ],
        "secure_alternatives": [
            "Use PreparedStatement with parameterized queries",
            "Enable FEATURE_SECURE_PROCESSING on XML factories",
            "Use java.security.SecureRandom for random numbers",
            "Avoid Java serialization; prefer JSON with strict typing",
            "Validate and sanitize all user inputs",
        ],
    },
    "kotlin": {
        "dangerous_functions": [
            "Runtime.exec",  # Command injection risk
            "ProcessBuilder",  # Command injection risk
            "ObjectInputStream",  # Deserialization vulnerability
            "ScriptEngine.eval",  # Code injection
        ],
        "unsafe_patterns": [
            "!!",  # Non-null assertion, runtime crash risk
            "createStatement",  # SQL injection, use PreparedStatement
            "TrustAllCerts",  # Disabled TLS validation
        ],
        "secure_alternatives": [
            "Use safe calls (?.) and requireNotNull instead of !!",
            "Use PreparedStatement with parameterized queries",
            "Use java.security.SecureRandom for random numbers",
            "Validate and sanitize all user inputs",
        ],
    },
    "csharp": {
        "dangerous_functions": [
            "Process.Start",  # Command injection risk
            "BinaryFormatter",  # Deserialization vulnerability
            "Assembly.Load",  # Code loading risk
            "XmlDocument.Load",  # XXE risk without secure resolver
        ],
        "unsafe_patterns": [
            "SqlCommand",  # SQL injection without parameters
            "MD5",  # Weak hash algorithm
            "SHA1",  # Weak hash algorithm
            "Random",  # Not cryptographically secure
            "unsafe",  # Memory safety bypass
        ],
        "secure_alternatives": [
            "Use SqlParameter for parameterized queries",
            "Use System.Text.Json instead of BinaryFormatter",
            "Use RandomNumberGenerator for secure random numbers",
            "Set XmlResolver = null to prevent XXE",
            "Validate and sanitize all user inputs",
        ],
    },
    "elixir": {
        "dangerous_functions": [
            "Code.eval_string",  # Code injection
            ":os.cmd",  # Command injection
            "System.cmd",  # Command injection with user input
            ":erlang.binary_to_term",  # Deserialization vulnerability
        ],
        "unsafe_patterns": [
            "String.to_atom",  # Atom table exhaustion (DoS)
            "raw: true",  # Raw SQL, injection risk
            "Plug.Conn.put_resp_header",  # Header injection if unvalidated
        ],
        "secure_alternatives": [
            "Use String.to_existing_atom instead of String.to_atom",
            "Use Ecto parameterized queries instead of raw SQL",
            "Use Plug.Crypto for secure tokens and comparison",
            "Validate and sanitize all user inputs",
        ],
    },
    "swift": {
        "dangerous_functions": [
            "NSTask",  # Command execution
            "Process",  # Command execution with user input
            "unsafeBitCast",  # Type safety bypass
            "UnsafeMutablePointer",  # Memory safety bypass
        ],
        "unsafe_patterns": [
            "try!",  # Crash on error
            "as!",  # Crash on failed cast
            "String(format:",  # Format string risk with user input
        ],
        "secure_alternatives": [
            "Use do/catch or try? instead of try!",
            "Use conditional casts (as?) with unwrapping",
            "Use SecRandomCopyBytes for secure random numbers",
            "Validate and sanitize all user inputs",
        ],
    },
    "scala": {
        "dangerous_functions": [
            "sys.process",  # Command injection risk
            "ObjectInputStream",  # Deserialization vulnerability
            "Class.forName",  # Reflection-based code loading
        ],
        "unsafe_patterns": [
            "createStatement",  # SQL injection, use PreparedStatement
            "asInstanceOf",  # Unchecked cast
            "null",  # Prefer Option
        ],
        "secure_alternatives": [
            "Use PreparedStatement or a typed query DSL",
            "Use Option instead of null",
            "Use java.security.SecureRandom for random numbers",
            "Validate and sanitize all user inputs",
        ],
    },
    "dart": {
        "dangerous_functions": [
            "Process.run",  # Command injection risk
            "Process.start",  # Command injection risk
            "dart:mirrors",  # Reflection-based code loading
        ],
        "unsafe_patterns": [
            "Random()",  # Not cryptographically secure
            "!",  # Null assertion, runtime crash risk
            "http://",  # Cleartext transport
        ],
        "secure_alternatives": [
            "Use Random.secure() for security-sensitive randomness",
            "Use null-aware operators instead of null assertions",
            "Use HTTPS for all network calls",
            "Validate and sanitize all user inputs",
        ],
    },
}


__all__ = ["LANGUAGE_SECURITY_SCANNERS", "LANGUAGE_SECURITY_RULES"]
