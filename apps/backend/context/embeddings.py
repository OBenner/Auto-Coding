"""
Embedding Generator for Semantic Search
========================================

Provides embedding generation with OpenAI API support and local fallback.
Used for semantic code search and similarity scoring in context optimization.

Features:
- OpenAI embeddings when API key is available (text-embedding-3-small)
- Local deterministic fallback using TF-IDF-like approach
- Caching to reduce API calls
- Batch embedding support

Usage:
    # Create generator (auto-detects OpenAI availability)
    generator = EmbeddingGenerator()

    # Generate embedding for a single text
    embedding = generator.generate_embedding("def hello_world(): pass")

    # Generate embeddings for multiple texts
    embeddings = generator.generate_embeddings_batch(["text1", "text2"])

    # Check which backend is being used
    if generator.is_using_openai():
        print("Using OpenAI embeddings")
    else:
        print("Using local fallback")
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from typing import Any

from core.sentry import capture_exception

logger = logging.getLogger(__name__)


# Default embedding dimensions
OPENAI_EMBEDDING_DIM = 1536  # text-embedding-3-small
LOCAL_EMBEDDING_DIM = 384  # Local fallback dimension


class EmbeddingGenerator:
    """
    Generate embeddings for semantic search using OpenAI or local fallback.

    Provides a unified interface for embedding generation with automatic
    provider selection based on API key availability.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        use_cache: bool = True,
        force_local: bool = False,
    ):
        """
        Initialize embedding generator.

        Args:
            model: OpenAI embedding model to use (default: text-embedding-3-small)
            use_cache: Enable caching to reduce API calls (default: True)
            force_local: Force use of local fallback even if OpenAI is available
        """
        self.model = model
        self.use_cache = use_cache
        self.force_local = force_local
        self._cache: dict[str, list[float]] = {}

        # Try to initialize OpenAI client
        self._openai_client = None
        self._using_openai = False

        if not force_local:
            self._initialize_openai()

        if not self._using_openai:
            logger.info("Using local embedding fallback (no OpenAI API key)")

    def _initialize_openai(self) -> None:
        """Initialize OpenAI client if API key is available."""
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not openai_api_key:
            logger.debug("OPENAI_API_KEY not found, using local fallback")
            return

        try:
            # Lazy import to avoid ImportError if openai package not installed
            import openai

            self._openai_client = openai.OpenAI(api_key=openai_api_key)
            self._using_openai = True
            logger.info(f"Initialized OpenAI embeddings with model: {self.model}")

        except ImportError:
            logger.warning(
                "openai package not installed, using local fallback. "
                "Install with: pip install openai"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")
            capture_exception(
                e,
                model=self.model,
                operation="initialize_openai",
            )

    def is_using_openai(self) -> bool:
        """Check if using OpenAI embeddings (vs local fallback)."""
        return self._using_openai

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this generator."""
        if self._using_openai:
            return OPENAI_EMBEDDING_DIM
        return LOCAL_EMBEDDING_DIM

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector (1536-dim for OpenAI, 384-dim for local)
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.get_embedding_dimension()

        # Check cache first
        if self.use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                return self._cache[cache_key]

        # Generate embedding
        if self._using_openai:
            embedding = self._generate_openai_embedding(text)
        else:
            embedding = self._generate_local_embedding(text)

        # Cache result
        if self.use_cache:
            cache_key = self._get_cache_key(text)
            self._cache[cache_key] = embedding

        return embedding

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        embeddings = []
        for text in texts:
            embeddings.append(self.generate_embedding(text))

        return embeddings

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        # Use MD5 hash of text as cache key
        return hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()

    def _generate_openai_embedding(self, text: str) -> list[float]:
        """
        Generate embedding using OpenAI API.

        Args:
            text: Input text

        Returns:
            OpenAI embedding vector
        """
        try:
            response = self._openai_client.embeddings.create(
                input=text,
                model=self.model,
            )
            return response.data[0].embedding

        except Exception as e:
            logger.warning(f"OpenAI embedding failed, falling back to local: {e}")
            capture_exception(
                e,
                text_length=len(text),
                model=self.model,
                operation="generate_openai_embedding",
            )
            # Fall back to local embedding on error
            return self._generate_local_embedding(text)

    def _generate_local_embedding(self, text: str) -> list[float]:
        """
        Generate embedding using local TF-IDF-like approach.

        This is a simple deterministic fallback that creates embeddings based on:
        1. Token frequency (TF-IDF approximation)
        2. Character n-grams
        3. Structural features (code-specific)

        Args:
            text: Input text

        Returns:
            Local embedding vector (384-dim)
        """
        # Normalize text
        text_lower = text.lower()

        # Extract features
        tokens = self._tokenize(text_lower)
        bigrams = self._extract_bigrams(text_lower)
        trigrams = self._extract_trigrams(text_lower)
        code_features = self._extract_code_features(text)

        # Build embedding vector
        embedding = [0.0] * LOCAL_EMBEDDING_DIM

        # Token frequency features (first 128 dimensions)
        for i, token in enumerate(tokens[:128]):
            hash_val = self._hash_feature(token, LOCAL_EMBEDDING_DIM)
            embedding[hash_val % 128] += 1.0

        # Bigram features (next 128 dimensions)
        for i, bigram in enumerate(bigrams[:128]):
            hash_val = self._hash_feature(bigram, LOCAL_EMBEDDING_DIM)
            embedding[128 + (hash_val % 128)] += 0.5

        # Trigram features (next 64 dimensions)
        for i, trigram in enumerate(trigrams[:64]):
            hash_val = self._hash_feature(trigram, LOCAL_EMBEDDING_DIM)
            embedding[256 + (hash_val % 64)] += 0.3

        # Code-specific features (last 64 dimensions)
        for i, feature in enumerate(code_features):
            hash_val = self._hash_feature(feature, LOCAL_EMBEDDING_DIM)
            embedding[320 + (hash_val % 64)] += 0.7

        # Normalize to unit length
        embedding = self._normalize_vector(embedding)

        return embedding

    def _tokenize(self, text: str) -> list[str]:
        """Extract tokens from text."""
        # Split on whitespace and common delimiters
        return re.findall(r'\w+', text)

    def _extract_bigrams(self, text: str) -> list[str]:
        """Extract character bigrams."""
        return [text[i:i+2] for i in range(len(text) - 1)]

    def _extract_trigrams(self, text: str) -> list[str]:
        """Extract character trigrams."""
        return [text[i:i+3] for i in range(len(text) - 2)]

    def _extract_code_features(self, text: str) -> list[str]:
        """Extract code-specific structural features."""
        features = []

        # Language keywords (common across Python, JS, etc.)
        keywords = [
            'def', 'class', 'function', 'import', 'from', 'return',
            'if', 'else', 'for', 'while', 'try', 'catch', 'async',
            'await', 'const', 'let', 'var', 'export', 'default'
        ]

        text_lower = text.lower()
        for keyword in keywords:
            if keyword in text_lower:
                features.append(f'keyword_{keyword}')

        # Structural patterns
        if '(' in text and ')' in text:
            features.append('has_function_call')
        if '{' in text and '}' in text:
            features.append('has_braces')
        if '[' in text and ']' in text:
            features.append('has_brackets')
        if '.' in text:
            features.append('has_dot_notation')
        if '->' in text or '=>' in text:
            features.append('has_arrow')

        return features

    def _hash_feature(self, feature: str, dim: int) -> int:
        """Hash a feature string to an index."""
        # Use MD5 hash for deterministic mapping
        hash_bytes = hashlib.md5(feature.encode(), usedforsecurity=False).digest()
        hash_int = int.from_bytes(hash_bytes[:4], byteorder='little')
        return hash_int % dim

    def _normalize_vector(self, vector: list[float]) -> list[float]:
        """Normalize vector to unit length."""
        magnitude = math.sqrt(sum(x * x for x in vector))

        if magnitude == 0:
            return vector

        return [x / magnitude for x in vector]

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
        logger.debug("Embedding cache cleared")

    def get_cache_size(self) -> int:
        """Get number of cached embeddings."""
        return len(self._cache)
