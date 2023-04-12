from fastapi import APIRouter, status, Depends, HTTPException

from models.orm import Account
from models.pydantic import AccountOut, AccountIn
from routers.users.utils import get_current_user, get_password_hash

router = APIRouter(prefix="/registration")


@router.post(
    "",
    response_model=AccountOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_account(
    account: AccountIn, current_user: Account | None = Depends(get_current_user)
):
    if current_user is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    pwd_hash = get_password_hash(account.password)
    return await AccountOut.from_tortoise_orm(
        await Account.create(**account.dict(), password_hash=pwd_hash)
    )
