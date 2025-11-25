from sqlmodel import Field, SQLModel


class BaseModel(SQLModel):
    """Base model using integer primary keys.

    The `id` field is optional to support model instantiation before database
    persistence. After saving, use the `pk` property for type-safe primary key access.
    """

    id: int | None = Field(default=None, primary_key=True)

    @property
    def pk(self) -> int:
        """Primary key for persisted models.

        Use this instead of `id` when working with models loaded from
        or saved to the database.

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
