"""File Upload Template"""

from typing import Any

from ..registry import Template


class FileUploadTemplate(Template):
    """Template for file upload functionality."""

    def __init__(self):
        super().__init__(
            name="file_upload",
            description="File upload with validation and storage",
            category="feature",
            parameters={
                "file_types": {
                    "type": list,
                    "required": True,
                    "description": "Allowed file types",
                },
                "max_size_mb": {
                    "type": int,
                    "required": True,
                    "description": "Maximum file size in MB",
                },
                "storage_type": {
                    "type": str,
                    "required": True,
                    "description": "Storage (local, s3, azure)",
                },
                "virus_scan": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Virus scanning",
                },
            },
        )

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        file_types = params["file_types"]
        max_size_mb = params["max_size_mb"]
        storage_type = params["storage_type"]
        virus_scan = params.get("virus_scan", True)

        return {
            "title": "File Upload Feature",
            "description": f"Secure file upload supporting {', '.join(file_types)} up to {max_size_mb}MB.",
            "rationale": "Enable users to upload files securely with validation and storage.",
            "user_stories": [
                "As a user, I want to upload files",
                "As a user, I want to see upload progress",
            ],
            "acceptance_criteria": [
                f"Support file types: {', '.join(file_types)}",
                f"Enforce {max_size_mb}MB file size limit",
                f"Store files in {storage_type}",
                "File validation before upload",
                "Upload progress indicator",
            ]
            + (["Virus scanning on upload"] if virus_scan else []),
            "technical_details": f"Storage: {storage_type}\nMax size: {max_size_mb}MB\nTypes: {', '.join(file_types)}",
            "test_coverage": ["Upload tests", "Validation tests", "Size limit tests"],
        }
