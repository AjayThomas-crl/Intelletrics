from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, ClientOptions, create_client

from config import SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL, require_supabase_config


bearer = HTTPBearer(auto_error=False)


@dataclass
class UserContext:
    user_id: str
    client: Client


def get_user_client(token: str) -> Client:
    require_supabase_config()
    return create_client(
        SUPABASE_URL,
        SUPABASE_PUBLISHABLE_KEY,
        options=ClientOptions(
            auto_refresh_token=False,
            persist_session=False,
            headers={"Authorization": f"Bearer {token}"},
        ),
    )


async def get_user_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> UserContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        client = get_user_client(credentials.credentials)
        response = client.auth.get_user(credentials.credentials)
        user = response.user
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return UserContext(user_id=str(user.id), client=client)
