#!/usr/bin/env python3
"""
Test Code Relationship Storage
===============================

Tests for the CodeRelationshipQueries module.
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from integrations.graphiti.queries_pkg.code_relationships import (
    CodeRelationshipQueries,
)
from integrations.graphiti.queries_pkg.schema import (
    EPISODE_TYPE_CLASS_INHERITANCE,
    EPISODE_TYPE_CODE_RELATIONSHIP,
    EPISODE_TYPE_FUNCTION_CALL,
    EPISODE_TYPE_IMPORT_DEPENDENCY,
)


class TestStoreRelationships:
    """Test relationship storage methods."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock GraphitiClient."""
        client = Mock()
        client.graphiti = Mock()
        client.graphiti.add_episode = AsyncMock(return_value=None)
        return client

    @pytest.fixture
    def queries(self, mock_client):
        """Create a CodeRelationshipQueries instance with mock client."""
        return CodeRelationshipQueries(
            client=mock_client, group_id="test_group", spec_context_id="test_spec"
        )

    @pytest.mark.asyncio
    async def test_store_relationships(self, queries, mock_client):
        """Test that all relationship storage methods work correctly."""
        # Test storing a function call
        result = await queries.add_function_call(
            caller="main",
            callee="helper",
            file_path="test.py",
            lineno=10,
            call_type="function",
            module=None,
        )

        assert result is True
        assert mock_client.graphiti.add_episode.called
        call_args = mock_client.graphiti.add_episode.call_args[1]

        # Verify episode content
        episode_body = json.loads(call_args["episode_body"])
        assert episode_body["type"] == EPISODE_TYPE_FUNCTION_CALL
        assert episode_body["caller"] == "main"
        assert episode_body["callee"] == "helper"
        assert episode_body["file_path"] == "test.py"
        assert episode_body["lineno"] == 10
        assert episode_body["call_type"] == "function"

        # Reset mock
        mock_client.graphiti.add_episode.reset_mock()

        # Test storing an import dependency
        result = await queries.add_import_dependency(
            importing_file="test.py",
            module="os",
            names=["path"],
            alias=None,
            lineno=1,
            is_from_import=True,
        )

        assert result is True
        assert mock_client.graphiti.add_episode.called
        call_args = mock_client.graphiti.add_episode.call_args[1]

        # Verify episode content
        episode_body = json.loads(call_args["episode_body"])
        assert episode_body["type"] == EPISODE_TYPE_IMPORT_DEPENDENCY
        assert episode_body["importing_file"] == "test.py"
        assert episode_body["module"] == "os"
        assert episode_body["names"] == ["path"]
        assert episode_body["is_from_import"] is True

        # Reset mock
        mock_client.graphiti.add_episode.reset_mock()

        # Test storing an inheritance relationship
        result = await queries.add_inheritance_relationship(
            child="MyClass",
            parent="BaseClass",
            file_path="test.py",
            lineno=5,
            parent_module="base",
        )

        assert result is True
        assert mock_client.graphiti.add_episode.called
        call_args = mock_client.graphiti.add_episode.call_args[1]

        # Verify episode content
        episode_body = json.loads(call_args["episode_body"])
        assert episode_body["type"] == EPISODE_TYPE_CLASS_INHERITANCE
        assert episode_body["child"] == "MyClass"
        assert episode_body["parent"] == "BaseClass"
        assert episode_body["file_path"] == "test.py"
        assert episode_body["lineno"] == 5
        assert episode_body["parent_module"] == "base"

    @pytest.mark.asyncio
    async def test_add_function_call(self, queries, mock_client):
        """Test storing a function call relationship."""
        result = await queries.add_function_call(
            caller="caller_func",
            callee="callee_func",
            file_path="src/main.py",
            lineno=42,
            call_type="method",
            module="utils",
        )

        assert result is True
        assert mock_client.graphiti.add_episode.called

        # Check episode parameters
        call_args = mock_client.graphiti.add_episode.call_args[1]
        assert call_args["group_id"] == "test_group"
        assert "caller_func" in call_args["name"]
        assert "callee_func" in call_args["name"]
        assert "Function call" in call_args["source_description"]

        # Check episode content
        episode_body = json.loads(call_args["episode_body"])
        assert episode_body["type"] == EPISODE_TYPE_FUNCTION_CALL
        assert episode_body["spec_id"] == "test_spec"
        assert episode_body["caller"] == "caller_func"
        assert episode_body["callee"] == "callee_func"
        assert episode_body["file_path"] == "src/main.py"
        assert episode_body["lineno"] == 42
        assert episode_body["call_type"] == "method"
        assert episode_body["module"] == "utils"

    @pytest.mark.asyncio
    async def test_add_import_dependency(self, queries, mock_client):
        """Test storing an import dependency relationship."""
        result = await queries.add_import_dependency(
            importing_file="src/main.py",
            module="pathlib",
            names=["Path", "PurePath"],
            alias=None,
            lineno=3,
            is_from_import=True,
        )

        assert result is True
        assert mock_client.graphiti.add_episode.called

        # Check episode parameters
        call_args = mock_client.graphiti.add_episode.call_args[1]
        assert call_args["group_id"] == "test_group"
        assert "pathlib" in call_args["name"]
        assert "Import dependency" in call_args["source_description"]

        # Check episode content
        episode_body = json.loads(call_args["episode_body"])
        assert episode_body["type"] == EPISODE_TYPE_IMPORT_DEPENDENCY
        assert episode_body["spec_id"] == "test_spec"
        assert episode_body["importing_file"] == "src/main.py"
        assert episode_body["module"] == "pathlib"
        assert episode_body["names"] == ["Path", "PurePath"]
        assert episode_body["lineno"] == 3
        assert episode_body["is_from_import"] is True

    @pytest.mark.asyncio
    async def test_add_inheritance_relationship(self, queries, mock_client):
        """Test storing a class inheritance relationship."""
        result = await queries.add_inheritance_relationship(
            child="ChildClass",
            parent="ParentClass",
            file_path="src/models.py",
            lineno=15,
            parent_module="base_models",
        )

        assert result is True
        assert mock_client.graphiti.add_episode.called

        # Check episode parameters
        call_args = mock_client.graphiti.add_episode.call_args[1]
        assert call_args["group_id"] == "test_group"
        assert "ChildClass" in call_args["name"]
        assert "ParentClass" in call_args["name"]
        assert "Class inheritance" in call_args["source_description"]

        # Check episode content
        episode_body = json.loads(call_args["episode_body"])
        assert episode_body["type"] == EPISODE_TYPE_CLASS_INHERITANCE
        assert episode_body["spec_id"] == "test_spec"
        assert episode_body["child"] == "ChildClass"
        assert episode_body["parent"] == "ParentClass"
        assert episode_body["file_path"] == "src/models.py"
        assert episode_body["lineno"] == 15
        assert episode_body["parent_module"] == "base_models"

    @pytest.mark.asyncio
    async def test_add_file_relationships(self, queries, mock_client):
        """Test storing all relationships from a file."""
        relationships = {
            "calls": [
                {
                    "caller": "main",
                    "callee": "helper",
                    "lineno": 10,
                    "call_type": "function",
                    "module": None,
                }
            ],
            "imports": [
                {
                    "module": "os",
                    "names": ["path"],
                    "alias": None,
                    "lineno": 1,
                    "is_from_import": True,
                }
            ],
            "inheritance": [
                {
                    "child": "MyClass",
                    "parent": "BaseClass",
                    "lineno": 5,
                    "parent_module": None,
                }
            ],
            "total_relationships": 3,
            "entities": ["main", "helper", "MyClass"],
        }

        result = await queries.add_file_relationships(
            file_path="test.py", relationships=relationships
        )

        assert result is True

        # Should have called add_episode 4 times:
        # 1 for file_relationships summary + 1 call + 1 import + 1 inheritance
        assert mock_client.graphiti.add_episode.call_count == 4

        # Check the summary episode (first call)
        first_call_args = mock_client.graphiti.add_episode.call_args_list[0][1]
        summary_body = json.loads(first_call_args["episode_body"])
        assert summary_body["type"] == EPISODE_TYPE_CODE_RELATIONSHIP
        assert summary_body["file_path"] == "test.py"
        assert summary_body["total_relationships"] == 3
        assert summary_body["calls_count"] == 1
        assert summary_body["imports_count"] == 1
        assert summary_body["inheritance_count"] == 1

    @pytest.mark.asyncio
    async def test_error_handling(self, queries, mock_client):
        """Test that errors are handled gracefully."""
        # Make add_episode raise an exception
        mock_client.graphiti.add_episode.side_effect = Exception("Test error")

        # Should return False on error, not raise
        result = await queries.add_function_call(
            caller="test",
            callee="test",
            file_path="test.py",
            lineno=1,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_empty_file_relationships(self, queries, mock_client):
        """Test storing relationships from an empty file."""
        relationships = {
            "calls": [],
            "imports": [],
            "inheritance": [],
            "total_relationships": 0,
            "entities": [],
        }

        result = await queries.add_file_relationships(
            file_path="empty.py", relationships=relationships
        )

        assert result is True

        # Should only call add_episode once for the summary
        assert mock_client.graphiti.add_episode.call_count == 1

        # Check the summary
        call_args = mock_client.graphiti.add_episode.call_args[1]
        summary_body = json.loads(call_args["episode_body"])
        assert summary_body["calls_count"] == 0
        assert summary_body["imports_count"] == 0
        assert summary_body["inheritance_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
