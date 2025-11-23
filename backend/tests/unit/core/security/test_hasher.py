"""Test suite for API Key security utilities."""

import pytest

from app.core.security.hasher import BCryptAPIKeyService


@pytest.fixture
def api_key_hasher() -> BCryptAPIKeyService:
    """Provide BCrypt API key hasher instance."""
    return BCryptAPIKeyService()


class TestBCryptAPIKeyService:
    """Test suite for BCrypt API key service."""

    def test_generate_key_returns_tuple(
        self, api_key_hasher: BCryptAPIKeyService
    ) -> None:
        """Test generate_key returns plaintext and hash tuple."""
        result = api_key_hasher.generate_key()

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_generate_key_plaintext_has_correct_prefix(
        self, api_key_hasher: BCryptAPIKeyService
    ) -> None:
        """Test generated key has sk_ prefix."""
        plaintext, _ = api_key_hasher.generate_key()

        assert plaintext.startswith("sk_")

    def test_generate_key_plaintext_has_correct_length(
        self, api_key_hasher: BCryptAPIKeyService
    ) -> None:
        """Test generated key has correct length (sk_ + 64 hex chars)."""
        plaintext, _ = api_key_hasher.generate_key()

        # sk_ (3) + 64 hex chars = 67
        assert len(plaintext) == 67

    def test_generate_key_hash_is_bcrypt_format(
        self, api_key_hasher: BCryptAPIKeyService
    ) -> None:
        """Test generated hash is in bcrypt format."""
        _, key_hash = api_key_hasher.generate_key()

        assert key_hash.startswith("$2b$")

    def test_generate_key_produces_unique_keys(
        self, api_key_hasher: BCryptAPIKeyService
    ) -> None:
        """Test each call generates unique key."""
        key1, _ = api_key_hasher.generate_key()
        key2, _ = api_key_hasher.generate_key()

        assert key1 != key2

    def test_hash_key_returns_bcrypt_hash(
        self, api_key_hasher: BCryptAPIKeyService
    ) -> None:
        """Test hash_key returns bcrypt formatted hash."""
        key_hash = api_key_hasher.hash_key("sk_test_key_12345")

        assert key_hash.startswith("$2b$")

    def test_verify_key_returns_true_for_matching_key(
        self, api_key_hasher: BCryptAPIKeyService
    ) -> None:
        """Test verify_key returns True for matching key and hash."""
        plaintext, key_hash = api_key_hasher.generate_key()

        result = api_key_hasher.verify_key(plaintext, key_hash)

        assert result is True

    def test_verify_key_returns_false_for_non_matching_key(
        self, api_key_hasher: BCryptAPIKeyService
    ) -> None:
        """Test verify_key returns False for non-matching key."""
        _, key_hash = api_key_hasher.generate_key()

        result = api_key_hasher.verify_key("sk_wrong_key_value", key_hash)

        assert result is False

    def test_extract_prefix_returns_first_12_chars(
        self, api_key_hasher: BCryptAPIKeyService
    ) -> None:
        """Test extract_prefix returns first 12 characters."""
        plaintext, _ = api_key_hasher.generate_key()

        prefix = api_key_hasher.extract_prefix(plaintext)

        assert len(prefix) == 12
        assert prefix == plaintext[:12]

    def test_extract_prefix_includes_sk_prefix(
        self, api_key_hasher: BCryptAPIKeyService
    ) -> None:
        """Test extracted prefix includes sk_ prefix."""
        plaintext, _ = api_key_hasher.generate_key()

        prefix = api_key_hasher.extract_prefix(plaintext)

        assert prefix.startswith("sk_")

    def test_verify_key_returns_false_for_malformed_hash(
        self, api_key_hasher: BCryptAPIKeyService
    ) -> None:
        """Test verify_key returns False for malformed hash instead of raising."""
        result = api_key_hasher.verify_key("sk_test_key_value", "invalid_hash_format")

        assert result is False
