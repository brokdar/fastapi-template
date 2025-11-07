"""Shared fixtures for base repository tests."""

from typing import Any
from uuid import UUID

import pytest

from app.core.base.models import IntModel, UUIDModel


class SampleIntModel(IntModel, table=True):
    """Sample model with integer ID for repository testing."""

    __table_args__ = {"extend_existing": True}

    name: str


class SampleUUIDModel(UUIDModel, table=True):
    """Sample model with UUID ID for repository testing."""

    __table_args__ = {"extend_existing": True}

    name: str


@pytest.fixture(scope="session")
def test_int_model() -> SampleIntModel:
    """Provide test model instance with integer ID."""
    return SampleIntModel(id=1, name="Test Model")


@pytest.fixture(scope="session")
def sample_uuid() -> UUID:
    """Provide sample UUID for testing."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture(scope="session")
def test_uuid_model(sample_uuid: UUID) -> SampleUUIDModel:
    """Provide test model instance with UUID ID."""
    return SampleUUIDModel(id=sample_uuid, name="Test UUID Model")


@pytest.fixture(scope="session")
def sample_data() -> dict[str, Any]:
    """Provide sample test data."""
    return {"key": "value", "number": 42}
