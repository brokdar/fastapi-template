"""Test suite for API Key service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.auth.providers.api_key.exceptions import (
    APIKeyExpiredError,
    APIKeyLimitExceededError,
    APIKeyNotFoundError,
    InvalidAPIKeyError,
)
from app.core.auth.providers.api_key.models import APIKey
from app.core.auth.providers.api_key.services import APIKeyService
from app.core.security.hasher import BCryptAPIKeyService
from tests.unit.core.auth.providers.api_key.conftest import (
    VALID_TEST_KEY,
    VALID_TEST_KEY_PREFIX,
)


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Provide mocked APIKeyRepository."""
    return AsyncMock()


@pytest.fixture
def mock_hasher() -> Mock:
    """Provide mocked APIKeyHasher."""
    hasher = Mock(spec=BCryptAPIKeyService)
    hasher.generate_key = Mock(return_value=("sk_test_key_1234", "$2b$12$hash"))
    hasher.extract_prefix = Mock(return_value="sk_test_key_")
    hasher.verify_key = Mock(return_value=True)
    return hasher


@pytest.fixture
def api_key_service(mock_repository: AsyncMock, mock_hasher: Mock) -> APIKeyService:
    """Provide APIKeyService instance with mocked dependencies."""
    return APIKeyService(
        repository=mock_repository,
        hasher=mock_hasher,
        max_per_user=5,
        default_expiration_days=30,
    )


class TestCreateKey:
    """Test suite for create_key method."""

    @pytest.mark.asyncio
    async def test_create_key_returns_plaintext_and_model(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test create_key returns plaintext key and APIKey model."""
        mock_repository.count_by_user = AsyncMock(return_value=0)
        mock_repository.create = AsyncMock(side_effect=lambda x: x)

        plaintext, api_key = await api_key_service.create_key(
            user_id=1,
            name="Test Key",
        )

        assert plaintext == "sk_test_key_1234"
        assert isinstance(api_key, APIKey)
        assert api_key.name == "Test Key"
        assert api_key.user_id == 1

    @pytest.mark.asyncio
    async def test_create_key_uses_default_expiration(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test create_key uses default expiration when not specified."""
        mock_repository.count_by_user = AsyncMock(return_value=0)
        mock_repository.create = AsyncMock(side_effect=lambda x: x)

        _, api_key = await api_key_service.create_key(user_id=1, name="Test Key")

        expected_expiry = datetime.now(UTC) + timedelta(days=30)
        assert api_key.expires_at is not None
        time_diff = abs((api_key.expires_at - expected_expiry).total_seconds())
        assert time_diff < 2

    @pytest.mark.asyncio
    async def test_create_key_uses_custom_expiration(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test create_key uses custom expiration when specified."""
        mock_repository.count_by_user = AsyncMock(return_value=0)
        mock_repository.create = AsyncMock(side_effect=lambda x: x)

        _, api_key = await api_key_service.create_key(
            user_id=1,
            name="Test Key",
            expires_in_days=7,
        )

        expected_expiry = datetime.now(UTC) + timedelta(days=7)
        assert api_key.expires_at is not None
        time_diff = abs((api_key.expires_at - expected_expiry).total_seconds())
        assert time_diff < 2

    @pytest.mark.asyncio
    async def test_create_key_raises_limit_exceeded_error(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test create_key raises APIKeyLimitExceededError when limit reached."""
        mock_repository.count_by_user = AsyncMock(return_value=5)  # At limit

        with pytest.raises(APIKeyLimitExceededError, match="Maximum API keys limit"):
            await api_key_service.create_key(user_id=1, name="Test Key")

        mock_repository.create.assert_not_called()


class TestDeleteKey:
    """Test suite for delete_key method."""

    @pytest.mark.asyncio
    async def test_delete_key_succeeds_for_owner(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test delete_key succeeds when user owns the key."""
        api_key = APIKey(
            id=1, user_id=1, key_hash="hash", key_prefix="sk_", name="Test"
        )
        mock_repository.get_by_id = AsyncMock(return_value=api_key)
        mock_repository.delete = AsyncMock()

        await api_key_service.delete_key(key_id=1, user_id=1)

        mock_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_raises_not_found_error_when_key_missing(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test delete_key raises APIKeyNotFoundError when key doesn't exist."""
        mock_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(APIKeyNotFoundError, match="API key not found"):
            await api_key_service.delete_key(key_id=999, user_id=1)

    @pytest.mark.asyncio
    async def test_raises_not_found_error_when_wrong_owner(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test delete_key raises APIKeyNotFoundError when user doesn't own key."""
        api_key = APIKey(
            id=1, user_id=2, key_hash="hash", key_prefix="sk_", name="Test"
        )
        mock_repository.get_by_id = AsyncMock(return_value=api_key)

        with pytest.raises(APIKeyNotFoundError, match="API key not found"):
            await api_key_service.delete_key(key_id=1, user_id=1)


class TestDeleteKeyAdmin:
    """Test suite for delete_key_admin method."""

    @pytest.mark.asyncio
    async def test_delete_key_admin_succeeds(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test delete_key_admin succeeds for any key."""
        api_key = APIKey(
            id=1, user_id=2, key_hash="hash", key_prefix="sk_", name="Test"
        )
        mock_repository.get_by_id = AsyncMock(return_value=api_key)
        mock_repository.delete = AsyncMock()

        await api_key_service.delete_key_admin(key_id=1, admin_id=99)

        mock_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_raises_not_found_error_when_key_missing(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test delete_key_admin raises APIKeyNotFoundError when key doesn't exist."""
        mock_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(APIKeyNotFoundError, match="API key not found"):
            await api_key_service.delete_key_admin(key_id=999, admin_id=99)


class TestListKeys:
    """Test suite for list_keys method."""

    @pytest.mark.asyncio
    async def test_list_keys_returns_user_keys(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test list_keys returns all keys for user."""
        keys = [
            APIKey(id=1, user_id=1, key_hash="h1", key_prefix="sk_1", name="Key 1"),
            APIKey(id=2, user_id=1, key_hash="h2", key_prefix="sk_2", name="Key 2"),
        ]
        mock_repository.get_by_user_id = AsyncMock(return_value=keys)

        result = await api_key_service.list_keys(user_id=1)

        assert len(result) == 2
        mock_repository.get_by_user_id.assert_called_once_with(1)


class TestValidateKey:
    """Test suite for validate_key method."""

    @pytest.mark.asyncio
    async def test_validate_key_returns_user_and_key_ids(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
        mock_hasher: Mock,
    ) -> None:
        """Test validate_key returns user_id and key_id for valid key."""
        api_key = APIKey(
            id=1,
            user_id=42,
            key_hash="$2b$12$hash",
            key_prefix=VALID_TEST_KEY_PREFIX,
            name="Test",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        mock_repository.get_by_prefix = AsyncMock(return_value=api_key)
        mock_repository.update_last_used = AsyncMock()

        user_id, key_id = await api_key_service.validate_key(VALID_TEST_KEY)

        assert user_id == 42
        assert key_id == 1
        mock_repository.update_last_used.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_raises_invalid_error_when_key_not_found(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test validate_key raises InvalidAPIKeyError when key not found."""
        mock_repository.get_by_prefix = AsyncMock(return_value=None)

        with pytest.raises(InvalidAPIKeyError, match="API key not found"):
            await api_key_service.validate_key(VALID_TEST_KEY)

    @pytest.mark.asyncio
    async def test_raises_expired_error_when_key_expired(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test validate_key raises APIKeyExpiredError when key is expired."""
        api_key = APIKey(
            id=1,
            user_id=1,
            key_hash="hash",
            key_prefix=VALID_TEST_KEY_PREFIX,
            name="Test",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        mock_repository.get_by_prefix = AsyncMock(return_value=api_key)

        with pytest.raises(APIKeyExpiredError, match="API key has expired"):
            await api_key_service.validate_key(VALID_TEST_KEY)

    @pytest.mark.asyncio
    async def test_raises_invalid_error_when_hash_mismatch(
        self,
        api_key_service: APIKeyService,
        mock_repository: AsyncMock,
        mock_hasher: Mock,
    ) -> None:
        """Test validate_key raises InvalidAPIKeyError when hash doesn't match."""
        api_key = APIKey(
            id=1,
            user_id=1,
            key_hash="hash",
            key_prefix=VALID_TEST_KEY_PREFIX,
            name="Test",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        mock_repository.get_by_prefix = AsyncMock(return_value=api_key)
        mock_hasher.verify_key = Mock(return_value=False)

        with pytest.raises(InvalidAPIKeyError, match="API key verification failed"):
            await api_key_service.validate_key(VALID_TEST_KEY)
