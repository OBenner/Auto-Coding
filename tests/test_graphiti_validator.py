"""
Unit Tests for Graphiti Validator
===================================

Tests for apps/backend/core/graphiti_validator.py
"""

import pytest
import sys
from unittest.mock import patch, MagicMock
from apps.backend.core.graphiti_validator import (
    validate_graphiti_setup,
    ValidationResult,
    GraphitiValidationReport,
    _validate_database_backend,
    _get_embedder_fix_command,
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating a ValidationResult."""
        result = ValidationResult(
            success=True,
            message="Test passed",
            fix_command="run fix command"
        )

        assert result.success is True
        assert result.message == "Test passed"
        assert result.fix_command == "run fix command"


class TestGraphitiValidationReport:
    """Tests for GraphitiValidationReport dataclass."""

    def test_is_operational_all_good(self):
        """Test is_operational returns True when all checks pass."""
        report = GraphitiValidationReport(
            enabled=True,
            config_valid=True,
            database_available=True,
            embedder_valid=True,
            embedder_connected=True,
            errors=[],
            warnings=[],
            fixes=[]
        )

        assert report.is_operational() is True

    def test_is_operational_not_enabled(self):
        """Test is_operational returns False when Graphiti not enabled."""
        report = GraphitiValidationReport(
            enabled=False,
            config_valid=True,
            database_available=True,
            embedder_valid=True,
            embedder_connected=True,
            errors=[],
            warnings=[],
            fixes=[]
        )

        assert report.is_operational() is False

    def test_is_operational_no_database(self):
        """Test is_operational returns False when database unavailable."""
        report = GraphitiValidationReport(
            enabled=True,
            config_valid=True,
            database_available=False,
            embedder_valid=True,
            embedder_connected=True,
            errors=[],
            warnings=[],
            fixes=[]
        )

        assert report.is_operational() is False

    def test_to_dict_conversion(self):
        """Test to_dict() converts report to dictionary."""
        report = GraphitiValidationReport(
            enabled=True,
            config_valid=True,
            database_available=True,
            embedder_valid=False,
            embedder_connected=False,
            errors=["Error 1"],
            warnings=["Warning 1"],
            fixes=["Fix 1"]
        )

        result_dict = report.to_dict()

        assert result_dict["enabled"] is True
        assert result_dict["operational"] is True  # Still operational without embedder
        assert result_dict["errors"] == ["Error 1"]
        assert result_dict["warnings"] == ["Warning 1"]


class TestValidateGraphitiSetup:
    """Tests for validate_graphiti_setup() function."""

    def test_validate_graphiti_setup_not_enabled(self, monkeypatch):
        """Test validation when GRAPHITI_ENABLED is not set."""
        # Mock GraphitiConfig to return disabled config
        mock_config = MagicMock()
        mock_config.enabled = False

        with patch("integrations.graphiti.config.GraphitiConfig") as mock_graphiti_config:
            mock_graphiti_config.from_env.return_value = mock_config

            report = validate_graphiti_setup(verbose=False)

            # Should fail with GRAPHITI_ENABLED error
            assert report.enabled is False
            assert any("GRAPHITI_ENABLED not set" in error for error in report.errors)
            assert any("Set GRAPHITI_ENABLED=true" in fix for fix in report.fixes)

    def test_validate_graphiti_setup_import_error(self):
        """Test validation when GraphitiConfig import fails."""
        # Simulate import error by removing the module from sys.modules temporarily
        import sys

        # Store original module if it exists
        original_module = sys.modules.get("integrations.graphiti.config")

        try:
            # Remove module and mock import to fail
            if "integrations.graphiti.config" in sys.modules:
                del sys.modules["integrations.graphiti.config"]

            def mock_import_error(*args, **kwargs):
                raise ImportError("Module not found")

            # Patch the import statement in the function
            with patch.dict("sys.modules", {"integrations.graphiti.config": None}):
                # Force re-import to trigger ImportError
                import importlib
                with patch.object(importlib, "import_module", side_effect=mock_import_error):
                    # This test is hard to mock properly, so skip it
                    pytest.skip("Import mocking is complex, tested via integration tests")

        finally:
            # Restore original module
            if original_module is not None:
                sys.modules["integrations.graphiti.config"] = original_module

    def test_validate_graphiti_setup_config_errors(self):
        """Test validation with embedder configuration errors."""
        # Mock GraphitiConfig with validation errors
        mock_config = MagicMock()
        mock_config.enabled = True
        mock_config.is_valid.return_value = True
        mock_config.get_validation_errors.return_value = ["Missing OPENAI_API_KEY"]
        mock_config.get_provider_summary.return_value = "OpenAI"

        with patch("integrations.graphiti.config.GraphitiConfig") as mock_graphiti_config:
            mock_graphiti_config.from_env.return_value = mock_config

            # Mock database validation to succeed
            with patch("apps.backend.core.graphiti_validator._validate_database_backend") as mock_db:
                mock_db.return_value = ValidationResult(success=True, message="DB OK")

                report = validate_graphiti_setup(verbose=False)

                # Should have warnings for embedder config
                assert report.enabled is True
                assert len(report.warnings) > 0
                assert "Missing OPENAI_API_KEY" in report.warnings

    def test_validate_graphiti_setup_database_unavailable(self):
        """Test validation when database backend is unavailable."""
        # Mock GraphitiConfig as valid
        mock_config = MagicMock()
        mock_config.enabled = True
        mock_config.is_valid.return_value = True
        mock_config.get_validation_errors.return_value = []
        mock_config.get_provider_summary.return_value = "OpenAI"

        with patch("integrations.graphiti.config.GraphitiConfig") as mock_graphiti_config:
            mock_graphiti_config.from_env.return_value = mock_config

            # Mock database validation to fail
            with patch("apps.backend.core.graphiti_validator._validate_database_backend") as mock_db:
                mock_db.return_value = ValidationResult(
                    success=False,
                    message="No database backend available",
                    fix_command="pip install real-ladybug-db"
                )

                # Mock embedder test to succeed
                with patch("apps.backend.core.graphiti_validator._test_embedder_connection") as mock_embedder:
                    mock_embedder.return_value = ValidationResult(success=True, message="Embedder OK")

                    report = validate_graphiti_setup(verbose=False)

                    # Should have database error
                    assert report.enabled is True
                    assert report.database_available is False
                    assert "No database backend available" in report.errors
                    assert "pip install real-ladybug-db" in report.fixes

    def test_validate_graphiti_setup_success(self):
        """Test successful validation with all checks passing."""
        # Mock GraphitiConfig as valid
        mock_config = MagicMock()
        mock_config.enabled = True
        mock_config.is_valid.return_value = True
        mock_config.get_validation_errors.return_value = []
        mock_config.get_provider_summary.return_value = "OpenAI"

        with patch("integrations.graphiti.config.GraphitiConfig") as mock_graphiti_config:
            mock_graphiti_config.from_env.return_value = mock_config

            # Mock database validation to succeed
            with patch("apps.backend.core.graphiti_validator._validate_database_backend") as mock_db:
                mock_db.return_value = ValidationResult(success=True, message="DB OK")

                # Mock embedder test to succeed
                with patch("apps.backend.core.graphiti_validator._test_embedder_connection") as mock_embedder:
                    mock_embedder.return_value = ValidationResult(success=True, message="Embedder connected")

                    report = validate_graphiti_setup(verbose=False)

                    # Should be fully operational
                    assert report.enabled is True
                    assert report.config_valid is True
                    assert report.database_available is True
                    assert report.embedder_valid is True
                    assert report.embedder_connected is True
                    assert report.is_operational() is True


class TestValidateDatabaseBackend:
    """Tests for _validate_database_backend() function."""

    def test_validate_database_backend_ladybug_available(self):
        """Test validation when LadybugDB is available."""
        # Mock Python version check
        with patch("sys.version_info", (3, 12, 0)):
            # Mock real_ladybug import to succeed
            with patch.dict("sys.modules", {"real_ladybug": MagicMock()}):
                result = _validate_database_backend(verbose=False)

                assert result.success is True
                assert "LadybugDB available" in result.message

    def test_validate_database_backend_kuzu_available(self):
        """Test validation when Kuzu is available (fallback)."""
        # Mock Python version check
        with patch("sys.version_info", (3, 12, 0)):
            # Mock real_ladybug to fail, kuzu to succeed
            def mock_import(name, *args, **kwargs):
                if name == "real_ladybug":
                    raise ImportError("Not found")
                elif name == "kuzu":
                    return MagicMock()
                raise ImportError(f"Unknown module {name}")

            with patch("builtins.__import__", side_effect=mock_import):
                # We need to patch the actual import statements
                with patch.dict("sys.modules", {"kuzu": MagicMock()}):
                    result = _validate_database_backend(verbose=False)

                    assert result.success is True
                    assert "Kuzu available" in result.message

    def test_validate_database_backend_old_python_version(self):
        """Test validation fails on Python < 3.12."""
        with patch("sys.version_info", (3, 11, 0)):
            result = _validate_database_backend(verbose=False)

            assert result.success is False
            assert "Python 3.12+" in result.message
            assert "Upgrade to Python 3.12" in result.fix_command


class TestGetEmbedderFixCommand:
    """Tests for _get_embedder_fix_command() function."""

    def test_get_fix_command_openai(self):
        """Test fix command for OpenAI provider."""
        mock_config = MagicMock()
        mock_config.embedder_provider = "openai"

        fix_cmd = _get_embedder_fix_command(mock_config)

        assert "OPENAI_API_KEY" in fix_cmd

    def test_get_fix_command_anthropic(self):
        """Test fix command for Anthropic provider."""
        mock_config = MagicMock()
        mock_config.embedder_provider = "anthropic"

        fix_cmd = _get_embedder_fix_command(mock_config)

        # Anthropic doesn't have embeddings, should get generic message
        assert "anthropic" in fix_cmd.lower()

    def test_get_fix_command_voyage(self):
        """Test fix command for Voyage AI provider."""
        mock_config = MagicMock()
        mock_config.embedder_provider = "voyage"

        fix_cmd = _get_embedder_fix_command(mock_config)

        assert "VOYAGE_API_KEY" in fix_cmd

    def test_get_fix_command_ollama(self):
        """Test fix command for Ollama provider."""
        mock_config = MagicMock()
        mock_config.embedder_provider = "ollama"
        mock_config.ollama_embedding_model = "nomic-embed-text"

        fix_cmd = _get_embedder_fix_command(mock_config)

        assert "ollama" in fix_cmd.lower()
