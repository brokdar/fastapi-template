from uuid import UUID

from sqlmodel import Field, SQLModel


class BaseModel[T: (int, UUID)](SQLModel):
    """Generic base model with configurable ID type.

    The `id` field is optional to support model instantiation before database
    persistence. After saving, use the `pk` property for type-safe primary key access.

    Type Parameters:
        T: The primary key type (int or UUID).
    """

    id: T | None = Field(default=None, primary_key=True)

    @property
    def pk(self) -> T:
        """Primary key for persisted models.

        Use this instead of `id` when working with models loaded from
        or saved to the database. Returns the correct type (int or UUID)
        based on the model's generic parameter.

        Returns:
            The model's primary key.

        Raises:
            ValueError: If accessed on an unpersisted model (id is None).
        """
        if self.id is None:
            raise ValueError(
                f"{self.__class__.__name__}.pk accessed but id is None. "
                "Model must be persisted before accessing pk."
            )
        return self.id


class IntModel(BaseModel[int]):
    """Base model using integer primary keys."""

    id: int | None = Field(default=None, primary_key=True)


class UUIDModel(BaseModel[UUID]):
    """Base model using UUID primary keys."""

    id: UUID | None = Field(default=None, primary_key=True)
