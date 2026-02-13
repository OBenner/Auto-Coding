"""
Fixtures for Collaboration Tests
==================================

Provides fixtures specific to testing the collaborative editing feature.
"""

import asyncio
import socket
from typing import Generator

import pytest


@pytest.fixture
def unused_tcp_port():
    """Find an unused TCP port for testing.

    Yields a port number that is guaranteed to be unused at the time of yielding.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    yield port
