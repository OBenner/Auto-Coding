"""Security Audit Template"""

from typing import Any

from ..registry import Template


class SecurityAuditTemplate(Template):
    """Template for security audit."""

    def __init__(self):
        super().__init__(
            name="security_audit",
            description="Security audit and vulnerability assessment",
            category="security",
            parameters={
                "audit_scope": {
                    "type": list,
                    "required": True,
                    "description": "Areas to audit (auth, api, database, dependencies)",
                },
                "compliance_standard": {
                    "type": str,
                    "required": False,
                    "default": "OWASP Top 10",
                    "description": "Compliance standard",
                },
                "penetration_testing": {
                    "type": bool,
                    "required": False,
                    "default": False,
                    "description": "Include pen testing",
                },
            },
        )

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        scope = params["audit_scope"]
        standard = params.get("compliance_standard", "OWASP Top 10")
        pen_test = params.get("penetration_testing", False)

        return {
            "title": "Security Audit",
            "description": f"Comprehensive security audit covering {', '.join(scope)}.",
            "rationale": "Identify and remediate security vulnerabilities to protect user data and system integrity.",
            "user_stories": [
                "As a security team, I want to identify vulnerabilities",
                "As a company, I want to comply with security standards",
            ],
            "acceptance_criteria": [
                f"Audit: {', '.join(scope)}",
                f"Check compliance with {standard}",
                "Document all findings with severity ratings",
                "Provide remediation recommendations",
            ]
            + (["Conduct penetration testing"] if pen_test else []),
            "technical_details": f"Scope: {', '.join(scope)}\nStandard: {standard}",
            "test_coverage": [
                "Security scans",
                "Vulnerability tests",
                "Compliance checks",
            ],
        }
