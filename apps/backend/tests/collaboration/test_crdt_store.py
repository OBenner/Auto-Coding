"""Unit tests for CRDT store operations."""

import pytest

from collaboration.crdt_store import CRDTStore, CrdtOperation, OpType


class TestCRDTStore:
    """Test CRDT store operations."""

    def test_optype_enum(self):
        """Test OpType enum values."""
        assert OpType.INSERT == "insert"
        assert OpType.DELETE == "delete"

    def test_crdt_store_creation(self):
        """Test CRDT store can be created."""
        store = CRDTStore(spec_id="test-spec")
        assert store is not None
        assert store.spec_id == "test-spec"

    def test_get_content(self):
        """Test get_content returns string."""
        store = CRDTStore(spec_id="test-spec")
        content = store.get_content()
        assert isinstance(content, str)

    def test_apply_insert_operation(self, tmp_path):
        """Test applying insert operation."""
        store = CRDTStore(spec_id="test", spec_dir=tmp_path)
        store.insert(
            content="Hello",
            position=0,
            author="user1",
            author_name="User 1"
        )
        assert "Hello" in store.get_content()

    def test_operation_history(self, tmp_path):
        """Test operation history tracking."""
        store = CRDTStore(spec_id="test", spec_dir=tmp_path)
        store.insert(content="A", position=0, author="u1", author_name="User 1")
        store.insert(content="B", position=1, author="u1", author_name="User 1")
        history = store.get_operation_history()
        assert len(history) >= 2
