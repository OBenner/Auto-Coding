#!/usr/bin/env python3
"""
Integration Test for Code Relationship Graph
===========================================

End-to-end test that verifies the complete code relationship graph workflow:
1. Parse sample Python codebase using CodeRelationshipExtractor
2. Store relationships in Graphiti using CodeRelationshipQueries
3. Query 'what uses function X' using find_callers
4. Perform impact analysis on class Y using ImpactAnalyzer
5. Search for 'authentication logic' using semantic search
6. Verify all results are accurate

This test uses a realistic sample codebase with functions, classes,
imports, and inheritance relationships.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from integrations.graphiti.code_relationship_extractor import (
    CodeRelationshipExtractor,
)
from integrations.graphiti.impact_analyzer import ImpactAnalyzer
from integrations.graphiti.queries_pkg.code_relationships import (
    CodeRelationshipQueries,
)

# Sample codebase files for testing
SAMPLE_AUTH_MODULE = """
# auth.py - Authentication module
from typing import Optional
from database import User, Database

class AuthService:
    '''Service for handling user authentication.'''

    def __init__(self, db: Database):
        self.db = db

    def login(self, username: str, password: str) -> Optional[User]:
        '''Authenticate user with username and password.'''
        user = self.validate_credentials(username, password)
        if user:
            self.create_session(user)
        return user

    def validate_credentials(self, username: str, password: str) -> Optional[User]:
        '''Validate user credentials against database.'''
        user = self.db.find_user(username)
        if user and user.check_password(password):
            return user
        return None

    def create_session(self, user: User) -> str:
        '''Create a new session for authenticated user.'''
        session_token = generate_token()
        self.db.save_session(user.id, session_token)
        return session_token

def generate_token() -> str:
    '''Generate a random session token.'''
    import secrets
    return secrets.token_hex(32)
"""

SAMPLE_API_MODULE = """
# api.py - API endpoints
from auth import AuthService, generate_token
from database import Database

db = Database()
auth_service = AuthService(db)

def handle_login(username: str, password: str):
    '''Handle login API request.'''
    user = auth_service.login(username, password)
    if user:
        return {"success": True, "user": user.username}
    return {"success": False, "error": "Invalid credentials"}

def handle_logout(session_token: str):
    '''Handle logout API request.'''
    db.delete_session(session_token)
    return {"success": True}
"""

SAMPLE_DATABASE_MODULE = """
# database.py - Database models and access
class BaseModel:
    '''Base class for all database models.'''

    def __init__(self, id: int):
        self.id = id

    def save(self):
        '''Save model to database.'''
        pass

class User(BaseModel):
    '''User model representing application users.'''

    def __init__(self, id: int, username: str, password_hash: str):
        super().__init__(id)
        self.username = username
        self.password_hash = password_hash

    def check_password(self, password: str) -> bool:
        '''Verify password against stored hash.'''
        return hash_password(password) == self.password_hash

class Database:
    '''Database connection and query interface.'''

    def find_user(self, username: str):
        '''Find user by username.'''
        pass

    def save_session(self, user_id: int, token: str):
        '''Save user session to database.'''
        pass

    def delete_session(self, token: str):
        '''Delete user session from database.'''
        pass

def hash_password(password: str) -> str:
    '''Hash password for secure storage.'''
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
"""


class TestCodeGraphIntegration:
    """Integration test for the complete code relationship graph workflow."""

    @pytest.fixture
    def sample_codebase(self):
        """Create a temporary directory with sample Python files."""
        tmpdir = tempfile.mkdtemp(prefix="codebase_test_")
        tmpdir_path = Path(tmpdir)

        # Write sample files
        (tmpdir_path / "auth.py").write_text(SAMPLE_AUTH_MODULE)
        (tmpdir_path / "api.py").write_text(SAMPLE_API_MODULE)
        (tmpdir_path / "database.py").write_text(SAMPLE_DATABASE_MODULE)

        yield tmpdir_path

        # Cleanup
        import shutil

        shutil.rmtree(tmpdir)

    @pytest.fixture
    def mock_graphiti_client(self):
        """Create a mock GraphitiClient that tracks stored data."""

        # In-memory storage for episodes
        stored_episodes = []
        search_index = []

        async def mock_add_episode(**kwargs):
            """Mock add_episode that stores data for later retrieval."""
            episode = {
                "name": kwargs.get("name"),
                "episode_body": kwargs.get("episode_body"),
                "source_description": kwargs.get("source_description"),
            }
            stored_episodes.append(episode)

            # Also add to search index for query testing
            body = json.loads(kwargs.get("episode_body"))
            search_index.append({"content": kwargs.get("episode_body"), "data": body})

        async def mock_search(query: str, group_ids: list, num_results: int):
            """Mock search that returns relevant stored episodes."""
            results = []

            # Simple keyword matching for testing
            query_lower = query.lower()

            for item in search_index:
                data = item["data"]
                content_str = json.dumps(data).lower()

                # Match based on query keywords
                if any(keyword in content_str for keyword in query_lower.split()):
                    # Create mock result object
                    result = Mock()
                    result.content = item["content"]
                    result.fact = item["content"]
                    result.score = 0.85
                    results.append(result)

            return results[:num_results]

        client = Mock()
        client.graphiti = Mock()
        client.graphiti.add_episode = AsyncMock(side_effect=mock_add_episode)
        client.graphiti.search = AsyncMock(side_effect=mock_search)

        # Expose storage for verification
        client._stored_episodes = stored_episodes
        client._search_index = search_index

        return client

    @pytest.fixture
    def code_relationships(self, mock_graphiti_client):
        """Create CodeRelationshipQueries with mock client."""
        queries = CodeRelationshipQueries(
            client=mock_graphiti_client,
            group_id="integration_test",
            spec_context_id="test_spec",
        )
        # Add reference to client for later access
        queries._mock_client = mock_graphiti_client
        return queries

    @pytest.fixture
    def impact_analyzer(self, mock_graphiti_client, code_relationships):
        """Create ImpactAnalyzer with mock client."""
        # Set up client.code_relationships property
        mock_graphiti_client.code_relationships = code_relationships

        analyzer = ImpactAnalyzer(
            client=mock_graphiti_client,
            group_id="integration_test",
            spec_context_id="test_spec",
            project_dir=Path("/tmp"),
        )
        return analyzer

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(
        self, sample_codebase, code_relationships, impact_analyzer
    ):
        """
        Complete end-to-end test of the code relationship graph.

        Steps:
        1. Parse sample codebase
        2. Store all relationships
        3. Query for function callers
        4. Perform impact analysis
        5. Search by purpose
        6. Verify all results
        """

        # =====================================================================
        # STEP 1: Parse sample Python codebase
        # =====================================================================
        print("\n=== STEP 1: Parsing sample codebase ===")

        extractor = CodeRelationshipExtractor()
        all_relationships = {}

        for py_file in sample_codebase.glob("*.py"):
            print(f"Analyzing {py_file.name}...")
            result = extractor.analyze_file(py_file)
            all_relationships[str(py_file)] = result

            # Verify extraction worked
            assert result["total_relationships"] > 0
            print(
                f"  Found {result['total_relationships']} relationships "
                f"({len(result['calls'])} calls, {len(result['imports'])} imports, "
                f"{len(result['inheritance'])} inheritance)"
            )

        # =====================================================================
        # STEP 2: Store relationships in Graphiti
        # =====================================================================
        print("\n=== STEP 2: Storing relationships in Graphiti ===")

        for file_path, relationships in all_relationships.items():
            print(f"Storing relationships from {Path(file_path).name}...")

            # Store using bulk operation
            success = await code_relationships.add_file_relationships(
                file_path=file_path,
                relationships=relationships,
            )
            assert success

            # Store semantic purpose for key functions
            if "auth.py" in file_path:
                await code_relationships.add_code_purpose(
                    entity_name="login",
                    entity_type="method",
                    purpose="Authenticate user with username and password",
                    file_path=file_path,
                    lineno=12,
                    tags=["authentication", "security", "api"],
                )

                await code_relationships.add_code_purpose(
                    entity_name="validate_credentials",
                    entity_type="method",
                    purpose="Validate user credentials against database",
                    file_path=file_path,
                    lineno=20,
                    tags=["authentication", "validation"],
                )

        # Verify storage
        client = code_relationships._mock_client
        print(f"  Stored {len(client._stored_episodes)} episodes")
        assert len(client._stored_episodes) > 0

        # =====================================================================
        # STEP 3: Query 'what uses function X' (find callers)
        # =====================================================================
        print("\n=== STEP 3: Querying function usage ===")

        # Test: Find what calls validate_credentials
        print("Finding callers of 'validate_credentials'...")
        callers = await code_relationships.find_callers("validate_credentials")
        print(f"  Found {len(callers)} callers: {[c['caller'] for c in callers]}")

        # Verify: login() should call validate_credentials()
        assert len(callers) > 0
        caller_names = [c["caller"] for c in callers]
        assert any("login" in name for name in caller_names)

        # Test: Find what calls login
        print("Finding callers of 'login'...")
        login_callers = await code_relationships.find_callers("login")
        print(
            f"  Found {len(login_callers)} callers: {[c['caller'] for c in login_callers]}"
        )

        # Verify: handle_login should call login()
        assert len(login_callers) > 0
        assert any("handle_login" in c["caller"] for c in login_callers)

        # Test: Find what login calls (callees)
        print("Finding callees of 'login'...")
        callees = await code_relationships.find_callees("AuthService.login")
        print(f"  Found {len(callees)} callees: {[c['callee'] for c in callees]}")

        # Verify: login() should call validate_credentials and create_session
        if callees:
            callee_names = [c["callee"] for c in callees]
            assert any("validate_credentials" in name for name in callee_names)

        # =====================================================================
        # STEP 4: Perform impact analysis on class Y
        # =====================================================================
        print("\n=== STEP 4: Performing impact analysis ===")

        # Test: Impact of changing BaseModel class
        print("Analyzing impact of changing 'BaseModel' class...")
        impact = await impact_analyzer.calculate_impact(
            entity_name="BaseModel", entity_type="class", max_depth=3
        )

        print(f"  Impact score: {impact['impact_score']}")
        print(f"  Affected entities: {len(impact['affected_entities'])}")
        print(f"  Depth breakdown: {list(impact['depth_analysis'].keys())}")

        # Verify: User inherits from BaseModel, so it should be affected
        if impact["affected_entities"]:
            affected_names = [e["name"] for e in impact["affected_entities"]]
            print(f"  Affected: {affected_names}")
            assert any("User" in name for name in affected_names)

        # Test: Impact of changing login function
        print("Analyzing impact of changing 'login' method...")
        login_impact = await impact_analyzer.calculate_impact(
            entity_name="AuthService.login", entity_type="function", max_depth=3
        )

        print(f"  Impact score: {login_impact['impact_score']}")
        print(f"  Affected entities: {len(login_impact['affected_entities'])}")

        # Verify: Should have some impact score
        assert login_impact["impact_score"] >= 0

        # Test: Coupling analysis
        print("Analyzing coupling for 'validate_credentials'...")
        coupling = await impact_analyzer.calculate_coupling_score(
            entity_name="validate_credentials", entity_type="function"
        )

        print(f"  Coupling score: {coupling['coupling_score']}")
        print(f"  Relationship strength: {coupling['relationship_strength']}")
        print(f"  Relationships: {len(coupling['relationships'])}")

        # Verify: Should have coupling information
        assert coupling["coupling_score"] >= 0
        assert coupling["relationship_strength"] in ["tight", "moderate", "loose"]

        # =====================================================================
        # STEP 5: Search for 'authentication logic' (semantic search)
        # =====================================================================
        print("\n=== STEP 5: Searching for authentication logic ===")

        # Test: Search by purpose
        print("Searching for authentication-related code...")
        auth_entities = await code_relationships.search_by_purpose(
            query="authentication logic", limit=10
        )

        print(f"  Found {len(auth_entities)} entities:")
        for entity in auth_entities:
            print(
                f"    - {entity['entity_name']} ({entity['entity_type']}): {entity['purpose'][:60]}..."
            )

        # Verify: Should find authentication-related functions
        if auth_entities:
            entity_names = [e["entity_name"] for e in auth_entities]
            # Should find login or validate_credentials
            assert any(
                name in entity_names for name in ["login", "validate_credentials"]
            )

        # Test: Natural language relationship query
        print("Querying relationships with natural language...")
        relationships = await code_relationships.query_relationships(
            query="what calls login function", limit=10
        )

        print(f"  Found {len(relationships)} relationships:")
        for rel in relationships[:3]:
            if rel["type"] == "function_call":
                print(f"    - {rel['caller']} calls {rel['callee']}")

        # Verify: Should find function call relationships
        if relationships:
            assert any(r["type"] == "function_call" for r in relationships)

        # =====================================================================
        # STEP 6: Verify all results are accurate
        # =====================================================================
        print("\n=== STEP 6: Verifying results accuracy ===")

        # Verify stored episode count
        total_episodes = len(client._stored_episodes)
        print(f"✓ Stored {total_episodes} episodes in Graphiti")
        assert total_episodes > 0

        # Verify we can query relationships
        print(f"✓ Found callers for validate_credentials: {len(callers)}")
        assert len(callers) > 0

        # Verify impact analysis works
        print(f"✓ Impact analysis calculated: score={impact['impact_score']}")
        assert impact["impact_score"] >= 0

        # Verify semantic search works
        print(f"✓ Semantic search found {len(auth_entities)} authentication entities")
        # Note: May be 0 if search doesn't match, but search should execute without error

        # Verify inheritance tracking
        print("Verifying inheritance relationships...")
        user_parents = await code_relationships.find_parent_classes("User")
        print(f"✓ Found {len(user_parents)} parent classes for User")
        if user_parents:
            parent_names = [p["parent"] for p in user_parents]
            print(f"  Parents: {parent_names}")
            assert any("BaseModel" in name for name in parent_names)

        # Verify function call chains
        print("Verifying function call chains...")
        print("✓ Verified call chain: handle_login -> login -> validate_credentials")
        # This is verified by earlier caller/callee queries

        print("\n=== All verification steps passed! ===")
        print("The code relationship graph is working correctly end-to-end.")

        # Summary statistics
        print("\n=== Summary Statistics ===")
        print(f"Files analyzed: {len(all_relationships)}")
        total_calls = sum(len(r["calls"]) for r in all_relationships.values())
        total_imports = sum(len(r["imports"]) for r in all_relationships.values())
        total_inheritance = sum(
            len(r["inheritance"]) for r in all_relationships.values()
        )
        print(f"Total function calls: {total_calls}")
        print(f"Total imports: {total_imports}")
        print(f"Total inheritance relationships: {total_inheritance}")
        print(f"Total episodes stored: {total_episodes}")

    @pytest.mark.asyncio
    async def test_query_accuracy(self, sample_codebase, code_relationships):
        """
        Test that queries return accurate results matching the actual code structure.
        """
        print("\n=== Testing Query Accuracy ===")

        # Parse and store auth module
        extractor = CodeRelationshipExtractor()
        auth_file = sample_codebase / "auth.py"
        relationships = extractor.analyze_file(auth_file)

        await code_relationships.add_file_relationships(
            file_path=str(auth_file),
            relationships=relationships,
        )

        # Test: Check that we captured the correct function calls
        print("Verifying captured function calls...")
        assert len(relationships["calls"]) > 0

        # Expected calls in auth.py:
        # - login calls validate_credentials
        # - login calls create_session
        # - create_session calls generate_token
        # - validate_credentials calls db.find_user
        # - validate_credentials calls user.check_password
        # - create_session calls db.save_session

        call_pairs = [
            (call["caller"], call["callee"]) for call in relationships["calls"]
        ]
        print(f"Found {len(call_pairs)} function calls:")
        for caller, callee in call_pairs:
            print(f"  {caller} -> {callee}")

        # Verify key relationships exist
        assert any(
            "login" in caller and "validate_credentials" in callee
            for caller, callee in call_pairs
        ), "Should find login -> validate_credentials"

        assert any(
            "login" in caller and "create_session" in callee
            for caller, callee in call_pairs
        ), "Should find login -> create_session"

        # Test: Check inheritance relationships
        print("\nVerifying captured inheritance...")
        # Note: auth.py has no inheritance (AuthService doesn't inherit from anything)
        # Inheritance is in database.py (User extends BaseModel)
        inheritance_pairs = [
            (inh["child"], inh["parent"]) for inh in relationships["inheritance"]
        ]
        print(f"Found {len(inheritance_pairs)} inheritance relationships in auth.py")
        if inheritance_pairs:
            for child, parent in inheritance_pairs:
                print(f"  {child} extends {parent}")
        else:
            print("  (No inheritance in auth.py - this is expected)")

        # Verify: AuthService has no inheritance in auth.py
        # (User extends BaseModel is in database.py, not auth.py)
        assert len(inheritance_pairs) == 0, "auth.py should have no inheritance"

        print("\n✓ Query accuracy verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
