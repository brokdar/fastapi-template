"""Test suite for signature_utils module."""

import inspect
from inspect import Parameter, Signature
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request

from app.core.auth.signature_utils import typed_signature
from app.domains.users.models import User


class TestTypedSignatureDecorator:
    """Test suite for typed_signature decorator factory."""

    def test_returns_callable_decorator(self, sample_signature: Signature) -> None:
        """Test factory returns callable decorator."""
        decorator = typed_signature(sample_signature)

        assert callable(decorator)

    @pytest.mark.asyncio
    async def test_preserves_async_function_type(
        self, sample_signature: Signature, mock_request: Mock, regular_user: User
    ) -> None:
        """Test decorated function remains async and executes correctly."""

        async def sample_func(request: Request, user_service: Any) -> User:
            return regular_user

        decorated = typed_signature(sample_signature)(sample_func)

        assert callable(decorated)
        result = decorated(mock_request, AsyncMock())
        assert inspect.iscoroutine(result)
        assert await result == regular_user

    def test_applies_makefun_signature_transformation(
        self, simple_signature: Signature
    ) -> None:
        """Test signature transformation via makefun.with_signature."""

        async def func(a: Any) -> str:
            return f"{a}"

        decorated = typed_signature(simple_signature)(func)
        applied_sig = inspect.signature(decorated)

        assert len(applied_sig.parameters) == 1
        assert "x" in applied_sig.parameters
        assert applied_sig.parameters["x"].annotation is int

    @pytest.mark.asyncio
    async def test_preserves_type_information_for_type_checker(
        self, sample_signature: Signature, mock_request: Mock
    ) -> None:
        """Test cast preserves type information at runtime."""

        async def func(request: Request, user_service: Any) -> dict[str, Any]:
            return {"request": request}

        decorated = typed_signature(sample_signature)(func)
        result = await decorated(mock_request, AsyncMock())

        assert result["request"] is mock_request

    @pytest.mark.asyncio
    async def test_works_with_generic_type_variables(
        self, simple_signature: Signature
    ) -> None:
        """Test decorator with generic ParamSpec and TypeVar."""

        async def func(x: int) -> int:
            return x * 2

        decorated = typed_signature(simple_signature)(func)
        result = await decorated(42)

        assert result == 84

    @pytest.mark.asyncio
    async def test_handles_functions_with_multiple_parameters(
        self, complex_signature: Signature, mock_request: Mock
    ) -> None:
        """Test signature with complex parameter sets."""

        async def func(
            request: Request, param1: str, param2: str | None = None
        ) -> dict[str, Any]:
            return {"request": request, "param1": param1, "param2": param2}

        decorated = typed_signature(complex_signature)(func)
        applied_sig = inspect.signature(decorated)

        assert len(applied_sig.parameters) == 3
        assert "request" in applied_sig.parameters
        assert "param1" in applied_sig.parameters
        assert "param2" in applied_sig.parameters
        assert applied_sig.parameters["param2"].default is None

        result = await decorated(mock_request, "test")
        assert result["param1"] == "test"
        assert result["param2"] is None

    @pytest.mark.asyncio
    async def test_preserves_original_implementation(
        self, sample_signature: Signature, mock_request: Mock, regular_user: User
    ) -> None:
        """Test function body executes correctly after decoration."""

        async def original_func(request: Request, user_service: Any) -> User:
            return regular_user

        decorated = typed_signature(sample_signature)(original_func)
        result = await decorated(mock_request, AsyncMock())

        assert result is regular_user
        assert result.id == regular_user.id
        assert result.username == regular_user.username

    def test_multiple_decorations_are_independent(self) -> None:
        """Test decorator applied to multiple functions independently."""
        sig1 = Signature(
            [Parameter("a", Parameter.POSITIONAL_OR_KEYWORD, annotation=int)]
        )
        sig2 = Signature(
            [Parameter("b", Parameter.POSITIONAL_OR_KEYWORD, annotation=str)]
        )

        async def func1(x: Any) -> Any:
            return x

        async def func2(y: Any) -> Any:
            return y

        decorated1 = typed_signature(sig1)(func1)
        decorated2 = typed_signature(sig2)(func2)

        sig1_applied = inspect.signature(decorated1)
        sig2_applied = inspect.signature(decorated2)

        assert "a" in sig1_applied.parameters
        assert "b" not in sig1_applied.parameters
        assert "b" in sig2_applied.parameters
        assert "a" not in sig2_applied.parameters

    def test_signature_with_return_annotation_preserved(
        self, signature_with_return: Signature
    ) -> None:
        """Test return type annotation preservation."""

        async def func(x: str) -> User:
            return User(
                id=1,
                username="test",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                hashed_password="hashed",
            )

        decorated = typed_signature(signature_with_return)(func)
        applied_sig = inspect.signature(decorated)

        assert applied_sig.return_annotation == User

    def test_cast_returns_same_object_identity(
        self, simple_signature: Signature
    ) -> None:
        """Test cast is runtime no-op preserving object identity."""

        async def func(a: Any) -> Any:
            return a

        decorator = typed_signature(simple_signature)
        decorated = decorator(func)

        assert callable(decorated)
        assert inspect.iscoroutinefunction(decorated)

    def test_works_with_empty_signature(self) -> None:
        """Test decorator with empty signature."""
        empty_sig = Signature([])

        async def func() -> str:
            return "result"

        decorated = typed_signature(empty_sig)(func)
        applied_sig = inspect.signature(decorated)

        assert len(applied_sig.parameters) == 0

    @pytest.mark.asyncio
    async def test_applies_signature_with_only_return_annotation(self) -> None:
        """Test signature with only return annotation no parameters."""
        sig = Signature([], return_annotation=str)

        async def func() -> str:
            return "test"

        decorated = typed_signature(sig)(func)
        applied_sig = inspect.signature(decorated)

        assert len(applied_sig.parameters) == 0
        assert applied_sig.return_annotation is str
        result = await decorated()
        assert result == "test"

    def test_overwrites_original_function_annotations(self) -> None:
        """Test new signature overrides original function annotations."""

        async def func(x: str) -> str:
            return x

        new_sig = Signature(
            [Parameter("x", Parameter.POSITIONAL_OR_KEYWORD, annotation=int)]
        )
        decorated = typed_signature(new_sig)(func)
        applied_sig = inspect.signature(decorated)

        assert applied_sig.parameters["x"].annotation is int
        assert applied_sig.parameters["x"].annotation is not str

    @pytest.mark.asyncio
    async def test_handles_many_parameters(self) -> None:
        """Test signature with many parameters preserved correctly."""
        many_params_sig = Signature(
            [
                Parameter(f"param{i}", Parameter.POSITIONAL_OR_KEYWORD, annotation=int)
                for i in range(10)
            ]
        )

        async def func(
            param0: int,
            param1: int,
            param2: int,
            param3: int,
            param4: int,
            param5: int,
            param6: int,
            param7: int,
            param8: int,
            param9: int,
        ) -> int:
            return (
                param0
                + param1
                + param2
                + param3
                + param4
                + param5
                + param6
                + param7
                + param8
                + param9
            )

        decorated = typed_signature(many_params_sig)(func)
        applied_sig = inspect.signature(decorated)

        assert len(applied_sig.parameters) == 10
        for i in range(10):
            param_name = f"param{i}"
            assert param_name in applied_sig.parameters
            assert applied_sig.parameters[param_name].annotation is int

        result = await decorated(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
        assert result == 55
