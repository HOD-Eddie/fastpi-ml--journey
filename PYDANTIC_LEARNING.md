# Pydantic Learning Progress

## What I learned today

I started treating incoming data as untrusted input rather than assuming that
the dictionary I receive is already correct. Pydantic lets me describe the
shape of that input with normal Python types and then validates it when I build
a model.

### 1. Types are executable rules

`int`, `str`, `EmailStr`, and `bool` describe the expected shape of a value.
Pydantic can coerce some values, so I use `Field(strict=True)` when coercion
would hide a mistake. For example, a user ID supplied as `"9921"` is rejected
when the API contract requires a real integer.

### 2. Constraints make invalid states harder to create

`Field(min_length=3, max_length=20)` constrains a username, while
`Field(ge=18)` ensures an age is at least 18. `Literal` is useful when the
allowed values are a closed set, such as `free`, `basic`, and `premium`.

I like `Annotated[type, Field(...)]` because the type and its constraints stay
next to each other and remain readable as the model grows.

### 3. Nested models mirror real payloads

`UserSignupModel` contains a `SubscriptionModel`. This means the subscription
gets its own validation rules instead of becoming an unstructured dictionary.
The same idea scales to orders, configuration files, and event payloads.

### 4. Custom validators fill the gaps

Built-in constraints cannot express every business rule. The username validator
rejects spaces and normalizes the accepted value to lowercase. A custom
validator should raise `ValueError`; Pydantic catches it and places the result
inside its structured `ValidationError`.

### 5. Configuration controls the boundary

`extra="forbid"` rejects fields that the model does not know about. This is
useful at an API boundary because a misspelled or unexpected setting should be
noticed instead of silently ignored.

## My experiments

`pydantic-test.py` is the focused challenge. It demonstrates one successful
payload, a payload with several independent failures, and a payload containing
an unexpected field. The examples are wrapped in a `__main__` guard so the
models can also be imported without printing output.

`mastering-pydantic.py` is the broader notebook-style exercise. It combines
UUID defaults, `EmailStr`, `SecretStr`, optional values, default factories,
date-time defaults, `Literal`, and a custom name validator.

## What I want to learn next

1. Compare `model_validate`, `model_validate_json`, and `model_dump` in an API.
2. Learn how Pydantic models become FastAPI request and response schemas.
3. Add tests for both successful parsing and each important failure case.
4. Explore model validators for rules involving more than one field.

## How to run the examples

```bash
python pydantic-test.py
python mastering-pydantic.py
```

The examples require Pydantic and its email validation dependency, usually
installed with `pip install pydantic[email]`.