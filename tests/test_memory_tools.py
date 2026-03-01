#!/usr/bin/env python3
"""
Tests for Memory Tools
======================

Tests the memory.py tools module functionality including:
- record_discovery tool for recording codebase discoveries
- record_gotcha tool for recording pitfalls
- get_session_context tool for retrieving session memory
- list_discoveries tool for listing all discoveries with optional filtering
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Store original modules for cleanup
_original_modules = {}
_mocked_module_names = [
    "claude_agent_sdk",
]

for name in _mocked_module_names:
    if name in sys.modules:
        _original_modules[name] = sys.modules[name]

# Mock claude_agent_sdk before importing memory tools
# The SDK isn't available in the test environment
mock_agent_sdk = MagicMock()


# Create a mock tool decorator that just returns the function
def mock_tool_decorator(name, description, params):
    def decorator(func):
        func._tool_name = name
        func._tool_description = description
        func._tool_params = params
        return func

    return decorator


mock_agent_sdk.tool = mock_tool_decorator
sys.modules["claude_agent_sdk"] = mock_agent_sdk

import agents.tools_pkg.tools.memory as _memory_tools_mod

# Ensure the memory tools module uses our mock tool decorator even if already imported
_memory_tools_mod.tool = mock_tool_decorator
_memory_tools_mod.SDK_TOOLS_AVAILABLE = True
from agents.tools_pkg.tools.memory import create_memory_tools


def _get_tool(tools, name):
    """Locate a tool by its _tool_name attribute instead of fragile positional indexing."""
    return next(t for t in tools if getattr(t, "_tool_name", None) == name)


# Cleanup fixture to restore original modules after all tests in this module
@pytest.fixture(scope="module", autouse=True)
def cleanup_mocked_modules():
    """Restore original modules after all tests in this module complete."""
    yield  # Run all tests first
    # Cleanup: restore original modules or remove mocks
    for name in _mocked_module_names:
        if name in _original_modules:
            sys.modules[name] = _original_modules[name]
        elif name in sys.modules:
            del sys.modules[name]


class TestCreateMemoryTools:
    """Tests for create_memory_tools function."""

    def test_creates_five_tools(self, spec_dir: Path, project_dir: Path):
        """create_memory_tools returns all five memory tools."""
        tools = create_memory_tools(spec_dir, project_dir)

        assert len(tools) == 5
        tool_names = [t._tool_name for t in tools]
        assert "record_discovery" in tool_names
        assert "record_gotcha" in tool_names
        assert "record_feedback" in tool_names
        assert "get_session_context" in tool_names
        assert "list_discoveries" in tool_names


class TestListDiscoveries:
    """Tests for list_discoveries tool."""

    async def test_list_discoveries_no_file(self, spec_dir: Path, project_dir: Path):
        """list_discoveries returns helpful message when codebase_map.json doesn't exist."""
        # Don't create codebase_map.json

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        list_discoveries = _get_tool(tools, "list_discoveries")

        # Call the tool
        result = await list_discoveries({})

        # Check result
        assert "content" in result
        assert len(result["content"]) == 1
        text = result["content"][0]["text"]

        assert "No discoveries found" in text
        assert "Use record_discovery to add codebase discoveries" in text

    async def test_list_discoveries_empty_discoveries(
        self, spec_dir: Path, project_dir: Path
    ):
        """list_discoveries handles empty discoveries object."""
        # Create codebase_map with empty discoveries
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        codebase_map = {
            "discovered_files": {},
            "last_updated": "2024-01-15T10:30:00",
        }
        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text(json.dumps(codebase_map, indent=2))

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        list_discoveries = _get_tool(tools, "list_discoveries")

        # Call the tool
        result = await list_discoveries({})

        # Check result
        text = result["content"][0]["text"]
        assert "No discoveries recorded yet" in text

    async def test_list_discoveries_single_category(
        self, spec_dir: Path, project_dir: Path
    ):
        """list_discoveries displays discoveries grouped by category."""
        # Create codebase_map with discoveries in one category
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        codebase_map = {
            "discovered_files": {
                "app/routes/auth.py": {
                    "description": "Handles authentication routes",
                    "category": "backend",
                    "discovered_at": "2024-01-15T10:30:00",
                },
                "app/models/user.py": {
                    "description": "User model with OAuth fields",
                    "category": "backend",
                    "discovered_at": "2024-01-15T10:31:00",
                },
            },
            "last_updated": "2024-01-15T10:31:00",
        }
        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text(json.dumps(codebase_map, indent=2))

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        list_discoveries = _get_tool(tools, "list_discoveries")

        # Call the tool
        result = await list_discoveries({})

        # Check result
        text = result["content"][0]["text"]

        assert "## All Discoveries (2 total)" in text
        assert "### Backend" in text
        assert "`app/routes/auth.py`: Handles authentication routes" in text
        assert "`app/models/user.py`: User model with OAuth fields" in text

    async def test_list_discoveries_multiple_categories(
        self, spec_dir: Path, project_dir: Path
    ):
        """list_discoveries groups discoveries by multiple categories."""
        # Create codebase_map with discoveries in multiple categories
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        codebase_map = {
            "discovered_files": {
                "app/routes/auth.py": {
                    "description": "Authentication routes",
                    "category": "backend",
                    "discovered_at": "2024-01-15T10:30:00",
                },
                "src/components/Login.tsx": {
                    "description": "Login component",
                    "category": "frontend",
                    "discovered_at": "2024-01-15T10:31:00",
                },
                "app/models/user.py": {
                    "description": "User model",
                    "category": "backend",
                    "discovered_at": "2024-01-15T10:32:00",
                },
                "docker-compose.yml": {
                    "description": "Docker services config",
                    "category": "infrastructure",
                    "discovered_at": "2024-01-15T10:33:00",
                },
            },
            "last_updated": "2024-01-15T10:33:00",
        }
        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text(json.dumps(codebase_map, indent=2))

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        list_discoveries = _get_tool(tools, "list_discoveries")

        # Call the tool
        result = await list_discoveries({})

        # Check result
        text = result["content"][0]["text"]

        assert "## All Discoveries (4 total)" in text
        assert "### Backend" in text
        assert "### Frontend" in text
        assert "### Infrastructure" in text
        assert "`app/routes/auth.py`: Authentication routes" in text
        assert "`src/components/Login.tsx`: Login component" in text
        assert "`app/models/user.py`: User model" in text
        assert "`docker-compose.yml`: Docker services config" in text

    async def test_list_discoveries_filter_by_category(
        self, spec_dir: Path, project_dir: Path
    ):
        """list_discoveries filters discoveries by category."""
        # Create codebase_map with multiple categories
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        codebase_map = {
            "discovered_files": {
                "app/routes/auth.py": {
                    "description": "Authentication routes",
                    "category": "backend",
                    "discovered_at": "2024-01-15T10:30:00",
                },
                "src/components/Login.tsx": {
                    "description": "Login component",
                    "category": "frontend",
                    "discovered_at": "2024-01-15T10:31:00",
                },
                "app/models/user.py": {
                    "description": "User model",
                    "category": "backend",
                    "discovered_at": "2024-01-15T10:32:00",
                },
            },
            "last_updated": "2024-01-15T10:32:00",
        }
        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text(json.dumps(codebase_map, indent=2))

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        list_discoveries = _get_tool(tools, "list_discoveries")

        # Call the tool with category filter
        result = await list_discoveries({"category": "backend"})

        # Check result
        text = result["content"][0]["text"]

        assert "## Discoveries (category: backend)" in text
        assert "### Backend" in text
        assert "`app/routes/auth.py`: Authentication routes" in text
        assert "`app/models/user.py`: User model" in text
        # Should NOT include frontend
        assert "Login.tsx" not in text

    async def test_list_discoveries_filter_no_matches(
        self, spec_dir: Path, project_dir: Path
    ):
        """list_discoveries returns message when category filter has no matches."""
        # Create codebase_map without the requested category
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        codebase_map = {
            "discovered_files": {
                "app/routes/auth.py": {
                    "description": "Authentication routes",
                    "category": "backend",
                    "discovered_at": "2024-01-15T10:30:00",
                },
            },
            "last_updated": "2024-01-15T10:30:00",
        }
        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text(json.dumps(codebase_map, indent=2))

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        list_discoveries = _get_tool(tools, "list_discoveries")

        # Call the tool with category filter that doesn't match
        result = await list_discoveries({"category": "frontend"})

        # Check result
        text = result["content"][0]["text"]

        assert "No discoveries found in category 'frontend'" in text

    async def test_list_discoveries_missing_category_field(
        self, spec_dir: Path, project_dir: Path
    ):
        """list_discoveries handles discoveries without category field (defaults to 'general')."""
        # Create codebase_map with missing category
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        codebase_map = {
            "discovered_files": {
                "README.md": {
                    "description": "Project documentation",
                    # No category field
                    "discovered_at": "2024-01-15T10:30:00",
                },
                "app/main.py": {
                    "description": "Main application",
                    "category": "backend",
                    "discovered_at": "2024-01-15T10:31:00",
                },
            },
            "last_updated": "2024-01-15T10:31:00",
        }
        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text(json.dumps(codebase_map, indent=2))

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        list_discoveries = _get_tool(tools, "list_discoveries")

        # Call the tool
        result = await list_discoveries({})

        # Check result
        text = result["content"][0]["text"]

        assert "## All Discoveries (2 total)" in text
        assert "### Backend" in text
        assert "### General" in text
        assert "`README.md`: Project documentation" in text
        assert "`app/main.py`: Main application" in text

    async def test_list_discoveries_invalid_json(
        self, spec_dir: Path, project_dir: Path
    ):
        """list_discoveries handles corrupted codebase_map.json gracefully."""
        # Create invalid JSON file
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text("{ invalid json }")

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        list_discoveries = _get_tool(tools, "list_discoveries")

        # Call the tool
        result = await list_discoveries({})

        # Check result
        text = result["content"][0]["text"]
        assert "Error listing discoveries" in text

    async def test_list_discoveries_categories_sorted_alphabetically(
        self, spec_dir: Path, project_dir: Path
    ):
        """list_discoveries displays categories in alphabetical order."""
        # Create codebase_map with categories that need sorting
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        codebase_map = {
            "discovered_files": {
                "file1.py": {
                    "description": "File 1",
                    "category": "zebra",
                    "discovered_at": "2024-01-15T10:30:00",
                },
                "file2.py": {
                    "description": "File 2",
                    "category": "alpha",
                    "discovered_at": "2024-01-15T10:31:00",
                },
                "file3.py": {
                    "description": "File 3",
                    "category": "beta",
                    "discovered_at": "2024-01-15T10:32:00",
                },
            },
            "last_updated": "2024-01-15T10:32:00",
        }
        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text(json.dumps(codebase_map, indent=2))

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        list_discoveries = _get_tool(tools, "list_discoveries")

        # Call the tool
        result = await list_discoveries({})

        # Check result
        text = result["content"][0]["text"]

        # Categories should be sorted: Alpha, Beta, Zebra
        alpha_pos = text.find("### Alpha")
        beta_pos = text.find("### Beta")
        zebra_pos = text.find("### Zebra")

        assert alpha_pos < beta_pos < zebra_pos

    async def test_list_discoveries_missing_description(
        self, spec_dir: Path, project_dir: Path
    ):
        """list_discoveries handles discoveries without description field."""
        # Create codebase_map with missing description
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        codebase_map = {
            "discovered_files": {
                "app/routes/api.py": {
                    # No description field
                    "category": "backend",
                    "discovered_at": "2024-01-15T10:30:00",
                },
            },
            "last_updated": "2024-01-15T10:30:00",
        }
        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text(json.dumps(codebase_map, indent=2))

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        list_discoveries = _get_tool(tools, "list_discoveries")

        # Call the tool
        result = await list_discoveries({})

        # Check result
        text = result["content"][0]["text"]

        assert "`app/routes/api.py`: No description" in text


class TestRecordDiscovery:
    """Tests for record_discovery tool."""

    async def test_record_discovery_creates_file(
        self, spec_dir: Path, project_dir: Path
    ):
        """record_discovery creates codebase_map.json if it doesn't exist."""
        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        record_discovery = _get_tool(tools, "record_discovery")

        # Call the tool
        result = await record_discovery(
            {
                "file_path": "app/main.py",
                "description": "Main application entry point",
                "category": "backend",
            }
        )

        # Check result
        text = result["content"][0]["text"]
        assert "Recorded discovery for 'app/main.py'" in text

        # Verify file was created
        codebase_map_file = spec_dir / "memory" / "codebase_map.json"
        assert codebase_map_file.exists()

        # Verify content
        codebase_map = json.loads(codebase_map_file.read_text())
        assert "app/main.py" in codebase_map["discovered_files"]
        assert (
            codebase_map["discovered_files"]["app/main.py"]["description"]
            == "Main application entry point"
        )
        assert codebase_map["discovered_files"]["app/main.py"]["category"] == "backend"

    async def test_record_discovery_appends_to_existing(
        self, spec_dir: Path, project_dir: Path
    ):
        """record_discovery appends to existing codebase_map.json."""
        # Create existing codebase_map
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        codebase_map = {
            "discovered_files": {
                "app/routes/auth.py": {
                    "description": "Authentication routes",
                    "category": "backend",
                    "discovered_at": "2024-01-15T10:30:00",
                },
            },
            "last_updated": "2024-01-15T10:30:00",
        }
        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text(json.dumps(codebase_map, indent=2))

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        record_discovery = _get_tool(tools, "record_discovery")

        # Call the tool
        result = await record_discovery(
            {
                "file_path": "app/models/user.py",
                "description": "User model",
                "category": "backend",
            }
        )

        # Check result
        text = result["content"][0]["text"]
        assert "Recorded discovery for 'app/models/user.py'" in text

        # Verify both discoveries exist
        codebase_map = json.loads(codebase_map_file.read_text())
        assert len(codebase_map["discovered_files"]) == 2
        assert "app/routes/auth.py" in codebase_map["discovered_files"]
        assert "app/models/user.py" in codebase_map["discovered_files"]

    async def test_record_discovery_updates_existing_entry(
        self, spec_dir: Path, project_dir: Path
    ):
        """record_discovery updates existing entry for the same file."""
        # Create existing codebase_map
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        codebase_map = {
            "discovered_files": {
                "app/main.py": {
                    "description": "Old description",
                    "category": "general",
                    "discovered_at": "2024-01-15T10:30:00",
                },
            },
            "last_updated": "2024-01-15T10:30:00",
        }
        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text(json.dumps(codebase_map, indent=2))

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        record_discovery = _get_tool(tools, "record_discovery")

        # Call the tool with updated info
        result = await record_discovery(
            {
                "file_path": "app/main.py",
                "description": "New description",
                "category": "backend",
            }
        )

        # Check result
        text = result["content"][0]["text"]
        assert "Recorded discovery for 'app/main.py'" in text

        # Verify entry was updated
        codebase_map = json.loads(codebase_map_file.read_text())
        assert len(codebase_map["discovered_files"]) == 1
        assert (
            codebase_map["discovered_files"]["app/main.py"]["description"]
            == "New description"
        )
        assert codebase_map["discovered_files"]["app/main.py"]["category"] == "backend"

    async def test_record_discovery_default_category(
        self, spec_dir: Path, project_dir: Path
    ):
        """record_discovery defaults to 'general' category if not specified."""
        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        record_discovery = _get_tool(tools, "record_discovery")

        # Call the tool without category
        result = await record_discovery(
            {
                "file_path": "README.md",
                "description": "Project documentation",
            }
        )

        # Check result
        text = result["content"][0]["text"]
        assert "Recorded discovery for 'README.md'" in text

        # Verify default category
        codebase_map_file = spec_dir / "memory" / "codebase_map.json"
        codebase_map = json.loads(codebase_map_file.read_text())
        assert codebase_map["discovered_files"]["README.md"]["category"] == "general"


class TestRecordGotcha:
    """Tests for record_gotcha tool."""

    async def test_record_gotcha_creates_file(self, spec_dir: Path, project_dir: Path):
        """record_gotcha creates gotchas.md if it doesn't exist."""
        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        record_gotcha = _get_tool(tools, "record_gotcha")

        # Call the tool
        result = await record_gotcha(
            {
                "gotcha": "Database connections must be closed manually",
                "context": "SQLAlchemy doesn't auto-close in worker threads",
            }
        )

        # Check result
        text = result["content"][0]["text"]
        assert "Recorded gotcha: Database connections must be closed manually" in text

        # Verify file was created
        gotchas_file = spec_dir / "memory" / "gotchas.md"
        assert gotchas_file.exists()

        content = gotchas_file.read_text()
        assert "# Gotchas & Pitfalls" in content
        assert "Database connections must be closed manually" in content
        assert "Context: SQLAlchemy doesn't auto-close in worker threads" in content

    async def test_record_gotcha_appends_to_existing(
        self, spec_dir: Path, project_dir: Path
    ):
        """record_gotcha appends to existing gotchas.md."""
        # Create existing gotchas file
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        gotchas_file = memory_dir / "gotchas.md"
        gotchas_file.write_text(
            "# Gotchas & Pitfalls\n\n## [2024-01-15 10:00]\nFirst gotcha\n"
        )

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        record_gotcha = _get_tool(tools, "record_gotcha")

        # Call the tool
        result = await record_gotcha(
            {
                "gotcha": "Second gotcha",
                "context": "Important context",
            }
        )

        # Check result
        text = result["content"][0]["text"]
        assert "Recorded gotcha: Second gotcha" in text

        # Verify both gotchas exist
        content = gotchas_file.read_text()
        assert "First gotcha" in content
        assert "Second gotcha" in content
        assert "Important context" in content


class TestGetSessionContext:
    """Tests for get_session_context tool."""

    async def test_get_session_context_no_memory(
        self, spec_dir: Path, project_dir: Path
    ):
        """get_session_context returns message when no memory exists."""
        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        get_session_context = _get_tool(tools, "get_session_context")

        # Call the tool
        result = await get_session_context({})

        # Check result
        text = result["content"][0]["text"]
        assert "No session memory found" in text
        assert "first session" in text

    async def test_get_session_context_with_discoveries(
        self, spec_dir: Path, project_dir: Path
    ):
        """get_session_context includes codebase discoveries."""
        # Create memory with discoveries
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        codebase_map = {
            "discovered_files": {
                "app/main.py": {
                    "description": "Main application",
                    "category": "backend",
                    "discovered_at": "2024-01-15T10:30:00",
                },
            },
            "last_updated": "2024-01-15T10:30:00",
        }
        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text(json.dumps(codebase_map, indent=2))

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        get_session_context = _get_tool(tools, "get_session_context")

        # Call the tool
        result = await get_session_context({})

        # Check result
        text = result["content"][0]["text"]
        assert "## Codebase Discoveries" in text
        assert "`app/main.py`: Main application" in text

    async def test_get_session_context_with_gotchas(
        self, spec_dir: Path, project_dir: Path
    ):
        """get_session_context includes gotchas."""
        # Create memory with gotchas
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        gotchas_file = memory_dir / "gotchas.md"
        gotchas_file.write_text(
            "# Gotchas & Pitfalls\n\n## [2024-01-15 10:00]\nDatabase connections\n"
        )

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        get_session_context = _get_tool(tools, "get_session_context")

        # Call the tool
        result = await get_session_context({})

        # Check result
        text = result["content"][0]["text"]
        assert "## Gotchas" in text
        assert "Database connections" in text

    async def test_get_session_context_limits_discoveries(
        self, spec_dir: Path, project_dir: Path
    ):
        """get_session_context limits discoveries to 20 entries."""
        # Create memory with many discoveries
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        discovered_files = {
            f"file{i}.py": {
                "description": f"Description {i}",
                "category": "backend",
                "discovered_at": "2024-01-15T10:30:00",
            }
            for i in range(30)
        }

        codebase_map = {
            "discovered_files": discovered_files,
            "last_updated": "2024-01-15T10:30:00",
        }
        codebase_map_file = memory_dir / "codebase_map.json"
        codebase_map_file.write_text(json.dumps(codebase_map, indent=2))

        # Get tools
        tools = create_memory_tools(spec_dir, project_dir)
        get_session_context = _get_tool(tools, "get_session_context")

        # Call the tool
        result = await get_session_context({})

        # Check result - should only have 20 discoveries
        text = result["content"][0]["text"]
        discovery_count = text.count("`file")
        assert discovery_count == 20
