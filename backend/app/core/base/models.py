from uuid import UUID

from sqlmodel import Field, SQLModel


class BaseModel[T: (int, UUID)](SQLModel):
    """Generic base model with configurable ID type.

    This base class supports both int and UUID primary keys through generics.
    Subclasses should specify the ID type when inheriting.
    """

    id: T | None = Field(default=None, primary_key=True)


class IntModel(BaseModel[int]):
    """Base model using integer primary keys.

    Convenience class for models that use integer IDs.
    """

    id: int | None = Field(default=None, primary_key=True)


class UUIDModel(BaseModel[UUID]):
    """Base model using UUID primary keys.

    Convenience class for models that use UUID IDs.
    """

    id: UUID | None = Field(default=None, primary_key=True)
