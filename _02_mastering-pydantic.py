# I am using this file as a notebook in script form. My goal is to build
# reliable data-handling foundations before moving deeper into MLOps.


# Pydantic uses Python type hints as the starting point for runtime validation.
# It can report several independent field errors in one ValidationError.
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator

class User(BaseModel):
    """A user profile showing common Pydantic field features."""

    uid: UUID = Field(default_factory=uuid4)
    # Annotated keeps the Python type and its validation constraints together.
    first_name: Annotated[str, Field(min_length=3, max_length=15)]
    email: EmailStr
    age: Annotated[int, Field(gt=0)]
    password: SecretStr
    bio_info: str | None = None 
    is_active: bool = True
    # A factory creates a fresh list for every User instead of sharing one list.
    certs: list[str] = Field(default_factory=list)
    user_created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    # Literal restricts a value to a known set of choices.
    gender: Literal["male", "female"] | None = None

    # Custom rules live here when `Field()` cannot describe the business invariant.
    # This validator keeps names normalized and rejects values that are structurally invalid.
    @field_validator("first_name")
    @classmethod
    def validate_firstname(cls, value: str) -> str:
        if not value.replace("-", "").isalnum():
            raise ValueError("firstname must be alphanumeric")
        return value.lower()

# Building a list of model instances demonstrates that Pydantic validates data
# before the objects are used anywhere else in the app.
users: list[User] = [
    User(first_name="Eddie", email="eddie@gmail.com", age=34, password="learning"),
    User(first_name="Grace", email="grace@gmail.com", age=35, password="learning"),
]

for user in users:
    print(f"{user.first_name}: created at {user.user_created_at.isoformat()}")