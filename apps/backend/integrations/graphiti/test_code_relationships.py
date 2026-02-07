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
    EPISODE_TYPE_CODE_PURPOSE,
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


class TestQueryRelationships:
    """Test relationship query methods."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock GraphitiClient."""
        client = Mock()
        client.graphiti = Mock()
        client.graphiti.search = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def queries(self, mock_client):
        """Create a CodeRelationshipQueries instance with mock client."""
        return CodeRelationshipQueries(
            client=mock_client, group_id="test_group", spec_context_id="test_spec"
        )

    @pytest.mark.asyncio
    async def test_find_callers(self, queries, mock_client):
        """Test finding all functions that call a specific function."""
        # Mock search results
        mock_result1 = Mock()
        mock_result1.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "main",
                "callee": "helper",
                "file_path": "src/main.py",
                "lineno": 10,
                "call_type": "function",
                "module": None,
            }
        )

        mock_result2 = Mock()
        mock_result2.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "process",
                "callee": "helper",
                "file_path": "src/process.py",
                "lineno": 25,
                "call_type": "function",
                "module": None,
            }
        )

        mock_result3 = Mock()
        mock_result3.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "helper",
                "callee": "utils",
                "file_path": "src/main.py",
                "lineno": 15,
                "call_type": "function",
                "module": None,
            }
        )

        mock_client.graphiti.search.return_value = [
            mock_result1,
            mock_result2,
            mock_result3,
        ]

        # Find callers of "helper"
        callers = await queries.find_callers("helper")

        # Should find main and process (both call helper), but not utils (helper calls utils)
        assert len(callers) == 2
        assert mock_client.graphiti.search.called

        caller_names = [c["caller"] for c in callers]
        assert "main" in caller_names
        assert "process" in caller_names

        # Verify details of first caller
        main_caller = next(c for c in callers if c["caller"] == "main")
        assert main_caller["file_path"] == "src/main.py"
        assert main_caller["lineno"] == 10
        assert main_caller["call_type"] == "function"

    @pytest.mark.asyncio
    async def test_find_callees(self, queries, mock_client):
        """Test finding all functions that a specific function calls."""
        # Mock search results
        mock_result1 = Mock()
        mock_result1.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "main",
                "callee": "helper",
                "file_path": "src/main.py",
                "lineno": 10,
                "call_type": "function",
                "module": None,
            }
        )

        mock_result2 = Mock()
        mock_result2.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "main",
                "callee": "process",
                "file_path": "src/main.py",
                "lineno": 12,
                "call_type": "function",
                "module": None,
            }
        )

        mock_result3 = Mock()
        mock_result3.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "helper",
                "callee": "utils",
                "file_path": "src/helper.py",
                "lineno": 5,
                "call_type": "function",
                "module": None,
            }
        )

        mock_client.graphiti.search.return_value = [
            mock_result1,
            mock_result2,
            mock_result3,
        ]

        # Find callees of "main"
        callees = await queries.find_callees("main")

        # Should find helper and process (main calls both), but not utils (helper calls utils)
        assert len(callees) == 2
        assert mock_client.graphiti.search.called

        callee_names = [c["callee"] for c in callees]
        assert "helper" in callee_names
        assert "process" in callee_names

        # Verify details of first callee
        helper_callee = next(c for c in callees if c["callee"] == "helper")
        assert helper_callee["file_path"] == "src/main.py"
        assert helper_callee["lineno"] == 10
        assert helper_callee["call_type"] == "function"

    @pytest.mark.asyncio
    async def test_find_callers_empty_result(self, queries, mock_client):
        """Test finding callers when no results exist."""
        mock_client.graphiti.search.return_value = []

        callers = await queries.find_callers("nonexistent_function")

        assert len(callers) == 0
        assert mock_client.graphiti.search.called

    @pytest.mark.asyncio
    async def test_find_callers_error_handling(self, queries, mock_client):
        """Test that errors are handled gracefully in find_callers."""
        mock_client.graphiti.search.side_effect = Exception("Search failed")

        # Should return empty list on error, not raise
        callers = await queries.find_callers("test")

        assert callers == []

    @pytest.mark.asyncio
    async def test_find_callers_deduplication(self, queries, mock_client):
        """Test that duplicate caller results are deduplicated."""
        # Same caller appearing twice
        mock_result1 = Mock()
        mock_result1.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "main",
                "callee": "helper",
                "file_path": "src/main.py",
                "lineno": 10,
                "call_type": "function",
                "module": None,
            }
        )

        mock_result2 = Mock()
        mock_result2.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "main",
                "callee": "helper",
                "file_path": "src/main.py",
                "lineno": 10,
                "call_type": "function",
                "module": None,
            }
        )

        mock_client.graphiti.search.return_value = [mock_result1, mock_result2]

        callers = await queries.find_callers("helper")

        # Should only have one entry despite two results
        assert len(callers) == 1
        assert callers[0]["caller"] == "main"


class TestInheritanceChains:
    """Test inheritance chain query methods."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock GraphitiClient."""
        client = Mock()
        client.graphiti = Mock()
        client.graphiti.search = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def queries(self, mock_client):
        """Create a CodeRelationshipQueries instance with mock client."""
        return CodeRelationshipQueries(
            client=mock_client, group_id="test_group", spec_context_id="test_spec"
        )

    @pytest.mark.asyncio
    async def test_find_parent_classes(self, queries, mock_client):
        """Test finding parent classes of a class."""
        # Mock search results
        mock_result1 = Mock()
        mock_result1.content = json.dumps(
            {
                "type": EPISODE_TYPE_CLASS_INHERITANCE,
                "child": "ChildClass",
                "parent": "ParentClass",
                "file_path": "src/models.py",
                "lineno": 10,
                "parent_module": None,
            }
        )

        mock_result2 = Mock()
        mock_result2.content = json.dumps(
            {
                "type": EPISODE_TYPE_CLASS_INHERITANCE,
                "child": "ChildClass",
                "parent": "AnotherParent",
                "file_path": "src/models.py",
                "lineno": 10,
                "parent_module": "mixins",
            }
        )

        # Result where ChildClass is the parent (should be ignored)
        mock_result3 = Mock()
        mock_result3.content = json.dumps(
            {
                "type": EPISODE_TYPE_CLASS_INHERITANCE,
                "child": "GrandChild",
                "parent": "ChildClass",
                "file_path": "src/models.py",
                "lineno": 20,
                "parent_module": None,
            }
        )

        mock_client.graphiti.search.return_value = [
            mock_result1,
            mock_result2,
            mock_result3,
        ]

        # Find parents of "ChildClass"
        parents = await queries.find_parent_classes("ChildClass")

        # Should find ParentClass and AnotherParent (ChildClass inherits from them)
        # but not GrandChild (GrandChild inherits from ChildClass)
        assert len(parents) == 2
        assert mock_client.graphiti.search.called

        parent_names = [p["parent"] for p in parents]
        assert "ParentClass" in parent_names
        assert "AnotherParent" in parent_names

        # Verify details of first parent
        parent_class = next(p for p in parents if p["parent"] == "ParentClass")
        assert parent_class["file_path"] == "src/models.py"
        assert parent_class["lineno"] == 10
        assert parent_class["parent_module"] is None

        # Verify parent with module
        another_parent = next(p for p in parents if p["parent"] == "AnotherParent")
        assert another_parent["parent_module"] == "mixins"

    @pytest.mark.asyncio
    async def test_find_child_classes(self, queries, mock_client):
        """Test finding child classes that inherit from a class."""
        # Mock search results
        mock_result1 = Mock()
        mock_result1.content = json.dumps(
            {
                "type": EPISODE_TYPE_CLASS_INHERITANCE,
                "child": "ChildClass1",
                "parent": "BaseClass",
                "file_path": "src/child1.py",
                "lineno": 5,
                "parent_module": None,
            }
        )

        mock_result2 = Mock()
        mock_result2.content = json.dumps(
            {
                "type": EPISODE_TYPE_CLASS_INHERITANCE,
                "child": "ChildClass2",
                "parent": "BaseClass",
                "file_path": "src/child2.py",
                "lineno": 8,
                "parent_module": None,
            }
        )

        # Result where BaseClass is the child (should be ignored)
        mock_result3 = Mock()
        mock_result3.content = json.dumps(
            {
                "type": EPISODE_TYPE_CLASS_INHERITANCE,
                "child": "BaseClass",
                "parent": "GrandParent",
                "file_path": "src/base.py",
                "lineno": 3,
                "parent_module": None,
            }
        )

        mock_client.graphiti.search.return_value = [
            mock_result1,
            mock_result2,
            mock_result3,
        ]

        # Find children of "BaseClass"
        children = await queries.find_child_classes("BaseClass")

        # Should find ChildClass1 and ChildClass2 (they inherit from BaseClass)
        # but not GrandParent (BaseClass inherits from GrandParent)
        assert len(children) == 2
        assert mock_client.graphiti.search.called

        child_names = [c["child"] for c in children]
        assert "ChildClass1" in child_names
        assert "ChildClass2" in child_names

        # Verify details
        child1 = next(c for c in children if c["child"] == "ChildClass1")
        assert child1["file_path"] == "src/child1.py"
        assert child1["lineno"] == 5

    @pytest.mark.asyncio
    async def test_get_inheritance_chain(self, queries, mock_client):
        """Test getting full inheritance chain from child to root."""

        async def mock_search(query, group_ids, num_results):
            """Mock search that returns different results based on query context."""
            # Simulate inheritance: GrandChild -> Child -> Parent -> BaseClass
            if "GrandChild" in query:
                result = Mock()
                result.content = json.dumps(
                    {
                        "type": EPISODE_TYPE_CLASS_INHERITANCE,
                        "child": "GrandChild",
                        "parent": "Child",
                        "file_path": "test.py",
                        "lineno": 1,
                        "parent_module": None,
                    }
                )
                return [result]
            elif "Child" in query:
                result = Mock()
                result.content = json.dumps(
                    {
                        "type": EPISODE_TYPE_CLASS_INHERITANCE,
                        "child": "Child",
                        "parent": "Parent",
                        "file_path": "test.py",
                        "lineno": 2,
                        "parent_module": None,
                    }
                )
                return [result]
            elif "Parent" in query:
                result = Mock()
                result.content = json.dumps(
                    {
                        "type": EPISODE_TYPE_CLASS_INHERITANCE,
                        "child": "Parent",
                        "parent": "BaseClass",
                        "file_path": "test.py",
                        "lineno": 3,
                        "parent_module": None,
                    }
                )
                return [result]
            else:
                # BaseClass has no parent
                return []

        mock_client.graphiti.search.side_effect = mock_search

        # Get inheritance chain for GrandChild
        chain = await queries.get_inheritance_chain("GrandChild")

        # Should get full chain: GrandChild -> Child -> Parent -> BaseClass
        assert len(chain) == 4
        assert chain == ["GrandChild", "Child", "Parent", "BaseClass"]

    @pytest.mark.asyncio
    async def test_get_inheritance_chain_no_parents(self, queries, mock_client):
        """Test inheritance chain for a class with no parents."""
        mock_client.graphiti.search.return_value = []

        # Get inheritance chain for a class with no parents
        chain = await queries.get_inheritance_chain("StandaloneClass")

        # Should only contain the class itself
        assert len(chain) == 1
        assert chain == ["StandaloneClass"]

    @pytest.mark.asyncio
    async def test_get_inheritance_chain_circular(self, queries, mock_client):
        """Test that circular inheritance is detected and stopped."""

        async def mock_search_circular(query, group_ids, num_results):
            """Mock search that simulates circular inheritance."""
            if "ClassA" in query:
                result = Mock()
                result.content = json.dumps(
                    {
                        "type": EPISODE_TYPE_CLASS_INHERITANCE,
                        "child": "ClassA",
                        "parent": "ClassB",
                        "file_path": "test.py",
                        "lineno": 1,
                        "parent_module": None,
                    }
                )
                return [result]
            elif "ClassB" in query:
                result = Mock()
                result.content = json.dumps(
                    {
                        "type": EPISODE_TYPE_CLASS_INHERITANCE,
                        "child": "ClassB",
                        "parent": "ClassA",
                        "file_path": "test.py",
                        "lineno": 2,
                        "parent_module": None,
                    }
                )
                return [result]
            return []

        mock_client.graphiti.search.side_effect = mock_search_circular

        # Get inheritance chain - should detect cycle
        chain = await queries.get_inheritance_chain("ClassA")

        # Should stop at ClassB and not continue infinitely
        assert len(chain) == 2
        assert chain == ["ClassA", "ClassB"]

    @pytest.mark.asyncio
    async def test_find_parent_classes_empty_result(self, queries, mock_client):
        """Test finding parents when no results exist."""
        mock_client.graphiti.search.return_value = []

        parents = await queries.find_parent_classes("NoParentClass")

        assert len(parents) == 0
        assert mock_client.graphiti.search.called

    @pytest.mark.asyncio
    async def test_find_parent_classes_error_handling(self, queries, mock_client):
        """Test that errors are handled gracefully in find_parent_classes."""
        mock_client.graphiti.search.side_effect = Exception("Search failed")

        # Should return empty list on error, not raise
        parents = await queries.find_parent_classes("test")

        assert parents == []

    @pytest.mark.asyncio
    async def test_find_child_classes_deduplication(self, queries, mock_client):
        """Test that duplicate child results are deduplicated."""
        # Same child appearing twice
        mock_result1 = Mock()
        mock_result1.content = json.dumps(
            {
                "type": EPISODE_TYPE_CLASS_INHERITANCE,
                "child": "ChildClass",
                "parent": "BaseClass",
                "file_path": "src/models.py",
                "lineno": 10,
                "parent_module": None,
            }
        )

        mock_result2 = Mock()
        mock_result2.content = json.dumps(
            {
                "type": EPISODE_TYPE_CLASS_INHERITANCE,
                "child": "ChildClass",
                "parent": "BaseClass",
                "file_path": "src/models.py",
                "lineno": 10,
                "parent_module": None,
            }
        )

        mock_client.graphiti.search.return_value = [mock_result1, mock_result2]

        children = await queries.find_child_classes("BaseClass")

        # Should only have one entry despite two results
        assert len(children) == 1
        assert children[0]["child"] == "ChildClass"


class TestNaturalLanguageQuery:
    """Test natural language query interface."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock GraphitiClient."""
        client = Mock()
        client.graphiti = Mock()
        client.graphiti.search = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def queries(self, mock_client):
        """Create a CodeRelationshipQueries instance with mock client."""
        return CodeRelationshipQueries(
            client=mock_client, group_id="test_group", spec_context_id="test_spec"
        )

    @pytest.mark.asyncio
    async def test_natural_language_query(self, queries, mock_client):
        """Test querying relationships with natural language."""
        # Mock search results with mixed relationship types
        mock_result1 = Mock()
        mock_result1.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "LoginComponent",
                "callee": "authenticate",
                "file_path": "src/login.py",
                "lineno": 15,
                "call_type": "function",
                "module": "auth",
            }
        )
        mock_result1.score = 0.9

        mock_result2 = Mock()
        mock_result2.content = json.dumps(
            {
                "type": EPISODE_TYPE_IMPORT_DEPENDENCY,
                "importing_file": "src/login.py",
                "module": "auth",
                "names": ["authenticate"],
                "alias": None,
                "lineno": 1,
                "is_from_import": True,
            }
        )
        mock_result2.score = 0.85

        mock_result3 = Mock()
        mock_result3.content = json.dumps(
            {
                "type": EPISODE_TYPE_CLASS_INHERITANCE,
                "child": "UserProfile",
                "parent": "BaseModel",
                "file_path": "src/models.py",
                "lineno": 10,
                "parent_module": "base",
            }
        )
        mock_result3.score = 0.75

        mock_client.graphiti.search.return_value = [
            mock_result1,
            mock_result2,
            mock_result3,
        ]

        # Query with natural language
        results = await queries.query_relationships(
            "show me all components using authenticate"
        )

        # Should find all three relationship types
        assert len(results) == 3
        assert mock_client.graphiti.search.called

        # Results should be sorted by score (highest first)
        assert results[0]["score"] == 0.9
        assert results[1]["score"] == 0.85
        assert results[2]["score"] == 0.75

        # Verify function call result
        function_call = next(r for r in results if r["type"] == "function_call")
        assert function_call["caller"] == "LoginComponent"
        assert function_call["callee"] == "authenticate"
        assert function_call["file_path"] == "src/login.py"
        assert function_call["lineno"] == 15

        # Verify import result
        import_result = next(r for r in results if r["type"] == "import")
        assert import_result["importing_file"] == "src/login.py"
        assert import_result["module"] == "auth"
        assert import_result["names"] == ["authenticate"]

        # Verify inheritance result
        inheritance = next(r for r in results if r["type"] == "inheritance")
        assert inheritance["child"] == "UserProfile"
        assert inheritance["parent"] == "BaseModel"
        assert inheritance["parent_module"] == "base"

    @pytest.mark.asyncio
    async def test_natural_language_query_with_filter(self, queries, mock_client):
        """Test querying relationships with type filter."""
        # Mock search results with mixed types
        mock_result1 = Mock()
        mock_result1.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "main",
                "callee": "helper",
                "file_path": "test.py",
                "lineno": 10,
                "call_type": "function",
                "module": None,
            }
        )
        mock_result1.score = 0.9

        mock_result2 = Mock()
        mock_result2.content = json.dumps(
            {
                "type": EPISODE_TYPE_IMPORT_DEPENDENCY,
                "importing_file": "test.py",
                "module": "os",
                "names": [],
                "alias": None,
                "lineno": 1,
                "is_from_import": False,
            }
        )
        mock_result2.score = 0.8

        mock_client.graphiti.search.return_value = [mock_result1, mock_result2]

        # Query with type filter for function calls only
        results = await queries.query_relationships(
            "what uses helper", include_types=[EPISODE_TYPE_FUNCTION_CALL]
        )

        # Should only include function calls
        assert len(results) == 1
        assert results[0]["type"] == "function_call"
        assert results[0]["callee"] == "helper"

    @pytest.mark.asyncio
    async def test_natural_language_query_deduplication(self, queries, mock_client):
        """Test that duplicate results are deduplicated."""
        # Same relationship appearing twice with different scores
        mock_result1 = Mock()
        mock_result1.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "main",
                "callee": "helper",
                "file_path": "test.py",
                "lineno": 10,
                "call_type": "function",
                "module": None,
            }
        )
        mock_result1.score = 0.9

        mock_result2 = Mock()
        mock_result2.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "main",
                "callee": "helper",
                "file_path": "test.py",
                "lineno": 10,
                "call_type": "function",
                "module": None,
            }
        )
        mock_result2.score = 0.8

        mock_client.graphiti.search.return_value = [mock_result1, mock_result2]

        results = await queries.query_relationships("find calls to helper")

        # Should only have one entry despite two results
        assert len(results) == 1
        assert results[0]["caller"] == "main"

    @pytest.mark.asyncio
    async def test_natural_language_query_empty_result(self, queries, mock_client):
        """Test querying when no results exist."""
        mock_client.graphiti.search.return_value = []

        results = await queries.query_relationships("find nonexistent function")

        assert len(results) == 0
        assert mock_client.graphiti.search.called

    @pytest.mark.asyncio
    async def test_natural_language_query_error_handling(self, queries, mock_client):
        """Test that errors are handled gracefully."""
        mock_client.graphiti.search.side_effect = Exception("Search failed")

        # Should return empty list on error, not raise
        results = await queries.query_relationships("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_natural_language_query_limit(self, queries, mock_client):
        """Test that limit parameter works correctly."""
        # Create 10 mock results
        mock_results = []
        for i in range(10):
            mock_result = Mock()
            mock_result.content = json.dumps(
                {
                    "type": EPISODE_TYPE_FUNCTION_CALL,
                    "caller": f"caller{i}",
                    "callee": "target",
                    "file_path": "test.py",
                    "lineno": i,
                    "call_type": "function",
                    "module": None,
                }
            )
            mock_result.score = 0.9 - (i * 0.05)  # Descending scores
            mock_results.append(mock_result)

        mock_client.graphiti.search.return_value = mock_results

        # Query with limit of 5
        results = await queries.query_relationships("find calls to target", limit=5)

        # Should only return 5 results
        assert len(results) == 5

        # Should be sorted by score (highest first)
        assert results[0]["caller"] == "caller0"
        assert results[4]["caller"] == "caller4"


class TestSemanticIndexing:
    """Test semantic indexing of code purposes."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock GraphitiClient."""
        client = Mock()
        client.graphiti = Mock()
        client.graphiti.add_episode = AsyncMock(return_value=None)
        client.graphiti.search = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def queries(self, mock_client):
        """Create a CodeRelationshipQueries instance with mock client."""
        return CodeRelationshipQueries(
            client=mock_client, group_id="test_group", spec_context_id="test_spec"
        )

    @pytest.mark.asyncio
    async def test_semantic_indexing(self, queries, mock_client):
        """Test indexing code purposes for semantic search."""
        # Test storing a function purpose with docstring and tags
        result = await queries.add_code_purpose(
            entity_name="authenticate_user",
            entity_type="function",
            purpose="Validates user credentials and creates a session token",
            file_path="src/auth/login.py",
            lineno=42,
            docstring="Authenticate user with email and password.\n\nReturns JWT token on success.",
            tags=["authentication", "security", "api"],
        )

        assert result is True
        assert mock_client.graphiti.add_episode.called

        # Verify episode parameters
        call_args = mock_client.graphiti.add_episode.call_args[1]
        assert call_args["group_id"] == "test_group"
        assert "purpose_authenticate_user" in call_args["name"]

        # Verify source description includes semantic information
        source_desc = call_args["source_description"]
        assert "authenticate_user" in source_desc
        assert "Validates user credentials" in source_desc
        assert "authentication" in source_desc
        assert "security" in source_desc

        # Verify episode content
        episode_body = json.loads(call_args["episode_body"])
        assert episode_body["type"] == EPISODE_TYPE_CODE_PURPOSE
        assert episode_body["spec_id"] == "test_spec"
        assert episode_body["entity_name"] == "authenticate_user"
        assert episode_body["entity_type"] == "function"
        assert episode_body["purpose"] == "Validates user credentials and creates a session token"
        assert episode_body["file_path"] == "src/auth/login.py"
        assert episode_body["lineno"] == 42
        assert "JWT token" in episode_body["docstring"]
        assert episode_body["tags"] == ["authentication", "security", "api"]

    @pytest.mark.asyncio
    async def test_add_code_purpose_minimal(self, queries, mock_client):
        """Test indexing code purpose with minimal parameters."""
        result = await queries.add_code_purpose(
            entity_name="UserModel",
            entity_type="class",
            purpose="Represents a user entity in the database",
            file_path="src/models/user.py",
        )

        assert result is True
        assert mock_client.graphiti.add_episode.called

        # Verify episode content has defaults for optional fields
        call_args = mock_client.graphiti.add_episode.call_args[1]
        episode_body = json.loads(call_args["episode_body"])
        assert episode_body["lineno"] == 0
        assert episode_body["docstring"] is None
        assert episode_body["tags"] == []

    @pytest.mark.asyncio
    async def test_add_code_purpose_error_handling(self, queries, mock_client):
        """Test that errors are handled gracefully when indexing purposes."""
        # Make add_episode raise an exception
        mock_client.graphiti.add_episode.side_effect = Exception("Indexing failed")

        # Should return False on error, not raise
        result = await queries.add_code_purpose(
            entity_name="test_func",
            entity_type="function",
            purpose="Test purpose",
            file_path="test.py",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_add_code_purpose_various_entity_types(self, queries, mock_client):
        """Test indexing different types of code entities."""
        # Test function
        await queries.add_code_purpose(
            entity_name="process_payment",
            entity_type="function",
            purpose="Handles payment processing with Stripe API",
            file_path="src/payments.py",
            tags=["payment", "api"],
        )

        # Test class
        await queries.add_code_purpose(
            entity_name="PaymentProcessor",
            entity_type="class",
            purpose="Manages payment transactions and refunds",
            file_path="src/payments.py",
            tags=["payment", "business_logic"],
        )

        # Test method
        await queries.add_code_purpose(
            entity_name="validate",
            entity_type="method",
            purpose="Validates payment card information",
            file_path="src/payments.py",
            tags=["validation", "payment"],
        )

        # Test module
        await queries.add_code_purpose(
            entity_name="auth",
            entity_type="module",
            purpose="Authentication and authorization utilities",
            file_path="src/auth/__init__.py",
            tags=["authentication", "security"],
        )

        # Should have called add_episode 4 times
        assert mock_client.graphiti.add_episode.call_count == 4

    @pytest.mark.asyncio
    async def test_search_by_purpose(self, queries, mock_client):
        """Test searching for code entities by their purpose."""
        # Mock search results with different entity types
        mock_result1 = Mock()
        mock_result1.content = json.dumps(
            {
                "type": EPISODE_TYPE_CODE_PURPOSE,
                "entity_name": "authenticate_user",
                "entity_type": "function",
                "purpose": "Validates user credentials and creates a session token",
                "file_path": "src/auth/login.py",
                "lineno": 42,
                "docstring": "Authenticate user with email and password.",
                "tags": ["authentication", "security", "api"],
            }
        )
        mock_result1.score = 0.95

        mock_result2 = Mock()
        mock_result2.content = json.dumps(
            {
                "type": EPISODE_TYPE_CODE_PURPOSE,
                "entity_name": "verify_token",
                "entity_type": "function",
                "purpose": "Verifies JWT token authenticity and expiration",
                "file_path": "src/auth/token.py",
                "lineno": 15,
                "docstring": "Verify JWT token is valid and not expired.",
                "tags": ["authentication", "security", "jwt"],
            }
        )
        mock_result2.score = 0.88

        mock_result3 = Mock()
        mock_result3.content = json.dumps(
            {
                "type": EPISODE_TYPE_CODE_PURPOSE,
                "entity_name": "AuthMiddleware",
                "entity_type": "class",
                "purpose": "Middleware for authentication and authorization",
                "file_path": "src/auth/middleware.py",
                "lineno": 10,
                "docstring": "Express middleware for route authentication.",
                "tags": ["authentication", "middleware"],
            }
        )
        mock_result3.score = 0.82

        # Include a non-CODE_PURPOSE result that should be filtered out
        mock_result4 = Mock()
        mock_result4.content = json.dumps(
            {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "caller": "login",
                "callee": "authenticate_user",
                "file_path": "src/login.py",
                "lineno": 20,
                "call_type": "function",
                "module": "auth",
            }
        )
        mock_result4.score = 0.75

        mock_client.graphiti.search.return_value = [
            mock_result1,
            mock_result2,
            mock_result3,
            mock_result4,
        ]

        # Search for authentication-related code
        results = await queries.search_by_purpose("authentication")

        # Should find 3 CODE_PURPOSE entries (function_call is filtered out)
        assert len(results) == 3
        assert mock_client.graphiti.search.called

        # Results should be sorted by score (highest first)
        assert results[0]["score"] == 0.95
        assert results[1]["score"] == 0.88
        assert results[2]["score"] == 0.82

        # Verify first result (highest score)
        assert results[0]["entity_name"] == "authenticate_user"
        assert results[0]["entity_type"] == "function"
        assert results[0]["purpose"] == "Validates user credentials and creates a session token"
        assert results[0]["file_path"] == "src/auth/login.py"
        assert results[0]["lineno"] == 42
        assert "authentication" in results[0]["tags"]

        # Verify second result
        assert results[1]["entity_name"] == "verify_token"
        assert results[1]["entity_type"] == "function"
        assert "jwt" in results[1]["tags"]

        # Verify third result
        assert results[2]["entity_name"] == "AuthMiddleware"
        assert results[2]["entity_type"] == "class"

    @pytest.mark.asyncio
    async def test_search_by_purpose_with_entity_type_filter(self, queries, mock_client):
        """Test searching by purpose with entity type filter."""
        # Mock results with mixed entity types
        mock_result1 = Mock()
        mock_result1.content = json.dumps(
            {
                "type": EPISODE_TYPE_CODE_PURPOSE,
                "entity_name": "validate_email",
                "entity_type": "function",
                "purpose": "Validates email address format",
                "file_path": "src/utils/validation.py",
                "lineno": 10,
                "docstring": None,
                "tags": ["validation"],
            }
        )
        mock_result1.score = 0.9

        mock_result2 = Mock()
        mock_result2.content = json.dumps(
            {
                "type": EPISODE_TYPE_CODE_PURPOSE,
                "entity_name": "Validator",
                "entity_type": "class",
                "purpose": "Email validation utilities",
                "file_path": "src/utils/validation.py",
                "lineno": 5,
                "docstring": None,
                "tags": ["validation"],
            }
        )
        mock_result2.score = 0.85

        mock_client.graphiti.search.return_value = [mock_result1, mock_result2]

        # Search with entity_type filter for functions only
        results = await queries.search_by_purpose("validation", entity_type="function")

        # Should only find the function, not the class
        assert len(results) == 1
        assert results[0]["entity_name"] == "validate_email"
        assert results[0]["entity_type"] == "function"

    @pytest.mark.asyncio
    async def test_search_by_purpose_empty_result(self, queries, mock_client):
        """Test searching when no results exist."""
        mock_client.graphiti.search.return_value = []

        results = await queries.search_by_purpose("nonexistent purpose")

        assert len(results) == 0
        assert mock_client.graphiti.search.called

    @pytest.mark.asyncio
    async def test_search_by_purpose_error_handling(self, queries, mock_client):
        """Test that errors are handled gracefully."""
        mock_client.graphiti.search.side_effect = Exception("Search failed")

        # Should return empty list on error, not raise
        results = await queries.search_by_purpose("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_by_purpose_deduplication(self, queries, mock_client):
        """Test that duplicate results are deduplicated."""
        # Same entity appearing twice with different scores
        mock_result1 = Mock()
        mock_result1.content = json.dumps(
            {
                "type": EPISODE_TYPE_CODE_PURPOSE,
                "entity_name": "process_payment",
                "entity_type": "function",
                "purpose": "Processes payment transactions",
                "file_path": "src/payments.py",
                "lineno": 10,
                "docstring": None,
                "tags": ["payment"],
            }
        )
        mock_result1.score = 0.9

        mock_result2 = Mock()
        mock_result2.content = json.dumps(
            {
                "type": EPISODE_TYPE_CODE_PURPOSE,
                "entity_name": "process_payment",
                "entity_type": "function",
                "purpose": "Processes payment transactions",
                "file_path": "src/payments.py",
                "lineno": 10,
                "docstring": None,
                "tags": ["payment"],
            }
        )
        mock_result2.score = 0.8

        mock_client.graphiti.search.return_value = [mock_result1, mock_result2]

        results = await queries.search_by_purpose("payment processing")

        # Should only have one entry despite two results
        assert len(results) == 1
        assert results[0]["entity_name"] == "process_payment"

    @pytest.mark.asyncio
    async def test_search_by_purpose_limit(self, queries, mock_client):
        """Test that limit parameter works correctly."""
        # Create 10 mock results
        mock_results = []
        for i in range(10):
            mock_result = Mock()
            mock_result.content = json.dumps(
                {
                    "type": EPISODE_TYPE_CODE_PURPOSE,
                    "entity_name": f"function_{i}",
                    "entity_type": "function",
                    "purpose": f"Does something {i}",
                    "file_path": "src/test.py",
                    "lineno": i * 10,
                    "docstring": None,
                    "tags": [],
                }
            )
            mock_result.score = 0.9 - (i * 0.05)  # Descending scores
            mock_results.append(mock_result)

        mock_client.graphiti.search.return_value = mock_results

        # Search with limit of 5
        results = await queries.search_by_purpose("test functions", limit=5)

        # Should only return 5 results
        assert len(results) == 5

        # Should be sorted by score (highest first)
        assert results[0]["entity_name"] == "function_0"
        assert results[4]["entity_name"] == "function_4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
