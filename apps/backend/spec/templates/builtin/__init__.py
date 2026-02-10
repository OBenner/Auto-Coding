"""
Built-in Templates
==================

Pre-built templates for common development tasks.
"""

from ..registry import Template, TemplateRegistry
from .admin_panel import AdminPanelTemplate
from .api_integration import ApiIntegrationTemplate
from .authentication import AuthenticationTemplate
from .caching import CachingLayerTemplate
from .ci_cd_pipeline import CiCdPipelineTemplate
from .crud_api import CrudApiTemplate
from .dashboard_widget import DashboardWidgetTemplate
from .database_migration import DatabaseMigrationTemplate
from .documentation import DocumentationTemplate
from .email_notifications import EmailNotificationsTemplate
from .error_handling import ErrorHandlingTemplate
from .export_data import ExportDataTemplate
from .file_upload import FileUploadTemplate
from .import_data import ImportDataTemplate
from .logging_system import LoggingSystemTemplate
from .monitoring_dashboard import MonitoringDashboardTemplate
from .pagination import PaginationTemplate
from .pdf_generation import PdfGenerationTemplate
from .performance_optimization import PerformanceOptimizationTemplate
from .search_feature import SearchFeatureTemplate
from .security_audit import SecurityAuditTemplate
from .settings_page import SettingsPageTemplate
from .test_suite import TestSuiteTemplate
from .ui_component import UiComponentTemplate
from .user_profile import UserProfileTemplate


def get_builtin_templates() -> list[Template]:
    """
    Get all built-in templates.

    Returns:
        List of built-in template instances
    """
    return [
        CrudApiTemplate(),
        AuthenticationTemplate(),
        DatabaseMigrationTemplate(),
        UiComponentTemplate(),
        ApiIntegrationTemplate(),
        FileUploadTemplate(),
        SearchFeatureTemplate(),
        PaginationTemplate(),
        CachingLayerTemplate(),
        EmailNotificationsTemplate(),
        PdfGenerationTemplate(),
        ExportDataTemplate(),
        ImportDataTemplate(),
        UserProfileTemplate(),
        SettingsPageTemplate(),
        DashboardWidgetTemplate(),
        AdminPanelTemplate(),
        LoggingSystemTemplate(),
        ErrorHandlingTemplate(),
        PerformanceOptimizationTemplate(),
        SecurityAuditTemplate(),
        TestSuiteTemplate(),
        DocumentationTemplate(),
        CiCdPipelineTemplate(),
        MonitoringDashboardTemplate(),
    ]


def register_builtin_templates(registry: TemplateRegistry) -> None:
    """
    Register all built-in templates with the registry.

    Args:
        registry: Template registry to register with
    """
    for template in get_builtin_templates():
        registry.register(template)
