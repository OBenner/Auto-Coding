"""
Built-in Templates
==================

Pre-built templates for common development tasks.
"""

from typing import Dict, List

from ..registry import Template, TemplateRegistry
from .authentication import AuthenticationTemplate
from .crud_api import CrudApiTemplate
from .database_migration import DatabaseMigrationTemplate
from .ui_component import UiComponentTemplate
from .api_integration import ApiIntegrationTemplate
from .file_upload import FileUploadTemplate
from .search_feature import SearchFeatureTemplate
from .pagination import PaginationTemplate
from .caching import CachingLayerTemplate
from .email_notifications import EmailNotificationsTemplate
from .pdf_generation import PdfGenerationTemplate
from .export_data import ExportDataTemplate
from .import_data import ImportDataTemplate
from .user_profile import UserProfileTemplate
from .settings_page import SettingsPageTemplate
from .dashboard_widget import DashboardWidgetTemplate
from .admin_panel import AdminPanelTemplate
from .logging_system import LoggingSystemTemplate
from .error_handling import ErrorHandlingTemplate
from .performance_optimization import PerformanceOptimizationTemplate
from .security_audit import SecurityAuditTemplate
from .test_suite import TestSuiteTemplate
from .documentation import DocumentationTemplate
from .ci_cd_pipeline import CiCdPipelineTemplate
from .monitoring_dashboard import MonitoringDashboardTemplate


def get_builtin_templates() -> List[Template]:
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
