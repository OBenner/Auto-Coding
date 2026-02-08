"""PDF Generation Template"""

from typing import Any, Dict
from ..registry import Template


class PdfGenerationTemplate(Template):
    """Template for PDF generation."""

    def __init__(self):
        super().__init__(
            name="pdf_generation",
            description="Generate PDF documents from templates",
            category="feature",
            parameters={
                "document_type": {"type": str, "required": True, "description": "Type of PDF (invoice, report, certificate)"},
                "template_engine": {"type": str, "required": False, "default": "html-to-pdf", "description": "PDF engine"},
                "include_graphics": {"type": bool, "required": False, "default": True, "description": "Include charts/images"},
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        doc_type = params["document_type"]
        engine = params.get("template_engine", "html-to-pdf")
        graphics = params.get("include_graphics", True)

        return {
            "title": f"PDF Generation - {doc_type.capitalize()}",
            "description": f"Generate {doc_type} PDFs using {engine}.",
            "rationale": f"Provide downloadable {doc_type} PDFs for users.",
            "user_stories": [
                f"As a user, I want to download {doc_type} as PDF",
                "As a user, I want PDFs to be properly formatted",
            ],
            "acceptance_criteria": [
                f"Generate {doc_type} PDFs",
                f"Using {engine} engine",
            ] + (["Include charts and images"] if graphics else []),
            "technical_details": f"Type: {doc_type}\nEngine: {engine}",
            "test_coverage": ["PDF generation tests", "Format validation tests", "Content accuracy tests"],
        }
