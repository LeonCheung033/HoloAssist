from typing import Any


def create_access_token(data: dict[str, Any]) -> str:
    # TODO: replace with JWT implementation
    return f"token::{data!r}"


def verify_access_token(token: str) -> dict[str, Any] | None:
    # TODO: replace with JWT verification
    if token.startswith("token::"):
        return {"sub": "placeholder"}
    return None