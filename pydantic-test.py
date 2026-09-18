# This exercise is my small streaming-service signup parser. It brings together
# constrained fields, strict types, nested models, custom validation, and model
# configuration in one realistic example.

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, field_validator

class SubscriptionModel(BaseModel):
    """The subscription choices that can be attached to a user account."""

    plan_name: Literal["free", "basic", "premium"] = "free"
    monthly_price: Annotated[float, Field(ge=0)]
    is_active: bool | None = True


class UserSignupModel(BaseModel):
    """Validated input for a new user registration."""

    model_config = ConfigDict(validate_by_name=True, extra="forbid")

    user_id: Annotated[int, Field(strict=True)]
    username: Annotated[str, Field(min_length=3, max_length=20)]
    email: EmailStr
    age: Annotated[int, Field(ge=18)]
    subscription: SubscriptionModel

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        # ValueError is converted into Pydantic's structured ValidationError.
        if " " in value:
            raise ValueError("username cannot contain spaces")
        return value.lower()

# Test Case 1: Valid Data (Should pass successfully)
valid_data = {
    # Field(strict=True) requires an actual int, not the string "9921".
    "user_id": 9921,
    "username": "coder_pro",
    "email": "test@example.com",
    "age": 25,
    "subscription": {
        "plan_name": "premium",
        "monthly_price": 14.99
    }
}

# Test Case 2: Invalid Data (Should throw standard ValidationError)
invalid_data = {
    "user_id": "9921",           # Invalid: String passed to strict integer field
    "username": "bad user name", # Invalid: Contains spaces
    "email": "not-an-email",     # Invalid: Bad email format
    "age": 16,                   # Invalid: Under 18
    "subscription": {
        "plan_name": "super",    # Invalid: Not a permitted plan option
        "monthly_price": -5.00   # Invalid: Price below 0
    }
}

# Test Case 3: Extra Field (Should throw an error due to extra='forbid')
extra_field_data = {
    "user_id": 1001,
    "username": "alice",
    "email": "alice@example.com",
    "age": 30,
    "subscription": {"plan_name": "free", "monthly_price": 0.00},
    "unexpected_setting": "dark_mode" 
}
def show_validation_example(label: str, data: dict) -> None:
    """Print either the parsed model or its structured validation failures."""
    print(f"\n--- {label} ---")
    try:
        user = UserSignupModel.model_validate(data)
    except ValidationError as error:
        print(error)
    else:
        print(user.model_dump_json(indent=2))


if __name__ == "__main__":
    show_validation_example("Valid data", valid_data)
    show_validation_example("Several invalid fields", invalid_data)
    show_validation_example("Unexpected extra field", extra_field_data)


print(UserSignupModel.model_validate(valid_data).model_dump_json(indent=2))