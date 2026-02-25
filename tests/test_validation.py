"""Tests for validation service."""

import pytest

from docagentline.services.validation import SchemaValidator


def test_schema_validator_valid_data(sample_schema):
    """Test validation with valid data."""
    validator = SchemaValidator()

    data = {
        "name": "Test Item",
        "amount": 100.50,
        "date": "2026-02-25",
    }

    result = validator.validate(data, sample_schema)

    assert result.is_valid
    assert len(result.errors) == 0


def test_schema_validator_missing_required(sample_schema):
    """Test validation with missing required field."""
    validator = SchemaValidator()

    data = {
        "name": "Test Item",
    }

    result = validator.validate(data, sample_schema)

    assert not result.is_valid
    assert len(result.errors) > 0
    assert any("amount" in error.message for error in result.errors)


def test_schema_validator_wrong_type(sample_schema):
    """Test validation with wrong type."""
    validator = SchemaValidator()

    data = {
        "name": "Test Item",
        "amount": "not a number",
    }

    result = validator.validate(data, sample_schema)

    assert not result.is_valid
    assert len(result.errors) > 0
