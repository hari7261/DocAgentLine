"""Tests for storage layer."""

import pytest
from pathlib import Path

from docagentline.storage import ContentHasher


def test_content_hasher():
    """Test content hashing."""
    hasher = ContentHasher()

    content1 = b"test content"
    content2 = b"test content"
    content3 = b"different content"

    hash1 = hasher.hash_content(content1)
    hash2 = hasher.hash_content(content2)
    hash3 = hasher.hash_content(content3)

    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 64  # SHA-256 hex digest


def test_string_hasher():
    """Test string hashing."""
    hasher = ContentHasher()

    text1 = "test string"
    text2 = "test string"
    text3 = "different string"

    hash1 = hasher.hash_string(text1)
    hash2 = hasher.hash_string(text2)
    hash3 = hasher.hash_string(text3)

    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 64
