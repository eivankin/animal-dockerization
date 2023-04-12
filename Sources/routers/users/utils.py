from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from passlib.context import CryptContext
from functools import wraps

from models.orm import Account, AccountRole

PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECURITY = HTTPBasic(auto_error=False)


def login_required(min_role: AccountRole = AccountRole.USER):
    """Декоратор, добавляющий проверку на авторизацию и нижнюю (включительно)
    границу уровня доступа пользователя"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if kwargs["current_user"] is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            if kwargs["current_user"].role < min_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return PWD_CONTEXT.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return PWD_CONTEXT.hash(password)


async def get_current_user(
    credentials: HTTPBasicCredentials = Depends(SECURITY),
) -> Account | None:
    if credentials is None:
        return None

    email = credentials.username
    user = await Account.get_or_none(email=email)
    if user is not None and verify_password(credentials.password, user.password_hash):
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
    )
