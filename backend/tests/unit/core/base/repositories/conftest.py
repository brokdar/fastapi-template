"""Shared fixtures for base repository tests."""

from typing import Any

import pytest

from app.core.base.models import BaseModel


class SampleModel(BaseModel, table=True):
    """Sample model with integer ID for repository testing."""

    __table_args__ = {"extend_existing": True}

    name: str


@pytest.fixture(scope="session")
def test_model() -> SampleModel:
    """Provide test model instance with integer ID."""
    return SampleModel(id=1, name="Test Model")


@pytest.fixture(scope="session")
def sample_data() -> dict[str, Any]:
    """Provide sample test data."""
    return {"key": "value", "number": 42}
