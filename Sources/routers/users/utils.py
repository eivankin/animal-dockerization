from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from passlib.context import CryptContext

from models.orm import Account

PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECURITY = HTTPBasic(auto_error=False)


def login_required(user: Account | None) -> None:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


def verify_password(plain_password, hashed_password):
    return PWD_CONTEXT.verify(plain_password, hashed_password)


def get_password_hash(password):
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
