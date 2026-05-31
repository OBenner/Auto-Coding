"""Gemini protobuf -> JSON-native conversion in the Google adapter.

Gemini function-call arguments come back as proto-plus containers
(``RepeatedComposite``, ``MapComposite``) that ``json.dumps`` cannot serialize
("Object of type RepeatedComposite is not JSON serializable"), which failed the
mini_pipeline probe. The adapter must de-protobuf them before the shared
tool-call parser and any downstream serialization.
"""

from __future__ import annotations

import json

from core.providers.adapters.google import (
    _google_arg_to_native,
    google_native_response_parts,
)


class _FakeMapComposite:
    """Mimics a proto-plus MapComposite: a mapping with .items(), not a dict."""

    def __init__(self, data):
        self._data = data

    def items(self):
        return self._data.items()


class _FakeRepeatedComposite:
    """Mimics a proto-plus RepeatedComposite: iterable, not a list."""

    def __init__(self, items):
        self._items = items

    def __iter__(self):
        return iter(self._items)


class _FakeFunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class _FakePart:
    def __init__(self, *, text=None, function_call=None):
        self.text = text
        self.function_call = function_call


class _FakeResponse:
    def __init__(self, parts):
        self.parts = parts
        self.candidates = []


def test_arg_to_native_converts_nested_protobuf_composites():
    args = _FakeMapComposite(
        {
            "path": "string_tools.py",
            "edits": _FakeRepeatedComposite(
                [_FakeMapComposite({"line": 1}), _FakeMapComposite({"line": 2})]
            ),
        }
    )
    native = _google_arg_to_native(args)
    assert native == {
        "path": "string_tools.py",
        "edits": [{"line": 1}, {"line": 2}],
    }
    json.dumps(native)  # the whole point: now serializable


def test_arg_to_native_passes_scalars_through():
    assert _google_arg_to_native("hi") == "hi"
    assert _google_arg_to_native(7) == 7
    assert _google_arg_to_native(None) is None


def test_native_response_parts_de_protobufs_function_calls():
    response = _FakeResponse(
        parts=[
            # Proto text parts still carry an (empty) function_call field.
            _FakePart(
                text="ok",
                function_call=_FakeFunctionCall(name="", args=_FakeMapComposite({})),
            ),
            _FakePart(
                function_call=_FakeFunctionCall(
                    name="write_file",
                    args=_FakeMapComposite(
                        {"path": "a.txt", "tags": _FakeRepeatedComposite(["x", "y"])}
                    ),
                )
            ),
        ]
    )
    native = google_native_response_parts(response)

    assert {"text": "ok"} in native
    call = next(p for p in native if "function_call" in p)["function_call"]
    assert call["name"] == "write_file"
    assert call["args"] == {"path": "a.txt", "tags": ["x", "y"]}
    json.dumps(native)  # no proto container survives
