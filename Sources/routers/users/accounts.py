from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from tortoise.exceptions import IntegrityError

from models.orm import Account, AccountRole
from models.pydantic import AccountOut, AccountIn, AccountInWithRole
from routers.users.utils import get_current_user, get_password_hash, login_required

router = APIRouter(prefix="/accounts")


@router.get("/search", response_model=list[AccountOut])
@login_required(AccountRole.ADMIN)
async def search_account(
    current_user: Account | None = Depends(get_current_user),
    first_name_like: str = Query(default=None, alias="firstName"),
    last_name_like: str = Query(default=None, alias="lastName"),
    email_like: str = Query(default=None, alias="email"),
    from_: int = Query(default=0, ge=0, alias="from"),
    size: int = Query(default=10, ge=1),
):
    query = Account.all()
    if first_name_like is not None and len(first_name_like) > 0:
        query = query.filter(first_name__icontains=first_name_like)
    if last_name_like is not None and len(last_name_like) > 0:
        query = query.filter(last_name__icontains=last_name_like)
    if email_like is not None and len(email_like) > 0:
        query = query.filter(email__icontains=email_like)

    return await AccountOut.from_queryset(
        query.order_by("id").offset(from_).limit(size)
    )


@router.get("/{account_id}", response_model=AccountOut)
@login_required()
async def get_account(
    account_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    if current_user.id != account_id and current_user.role != AccountRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return await AccountOut.from_queryset_single(Account.get(id=account_id))


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
@login_required(AccountRole.ADMIN)
async def create_account(
    new_account: AccountInWithRole,
    current_user: Account | None = Depends(get_current_user),
):
    pwd_hash = get_password_hash(new_account.password)
    return await AccountOut.from_tortoise_orm(
        await Account.create(**new_account.dict(), password_hash=pwd_hash)
    )


@router.put("/{account_id}", response_model=AccountOut)
@login_required()
async def update_account(
    new_account: AccountInWithRole,
    account_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    if current_user.id != account_id and current_user.role != AccountRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    account = await Account.get(id=account_id)
    await account.update_from_dict(new_account.dict())
    pwd_hash = get_password_hash(new_account.password)
    account.password_hash = pwd_hash
    await account.save()
    return account


@router.delete("/{account_id}")
@login_required()
async def delete_account(
    account_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    if current_user.id != account_id and current_user.role != AccountRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    account = await Account.get(id=account_id)
    try:
        await account.delete()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
