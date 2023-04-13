from fastapi import APIRouter, Path, Depends, status

from models.orm import Account, Area, AccountRole
from models.pydantic import AreaOut, AreaIn
from routers.users.utils import login_required, get_current_user

router = APIRouter(prefix="/areas")


@router.get("/{area_id}", response_model=AreaOut)
@login_required()
async def get_area(
    area_id: int = Path(ge=1),
    current_user: Account = Depends(get_current_user),
):
    area = await Area.get(id=area_id)
    return await AreaOut.from_tortoise_orm(area)


@router.post("", response_model=AreaOut, status_code=status.HTTP_201_CREATED)
@login_required(AccountRole.ADMIN)
async def create_area(
    new_area: AreaIn,
    current_user: Account = Depends(get_current_user),
):
    area = await Area.create(**new_area.dict())
    return await AreaOut.from_tortoise_orm(area)


@router.put("/{area_id}", response_model=AreaOut)
@login_required(AccountRole.ADMIN)
async def update_area(
    new_area: AreaIn,
    area_id: int = Path(ge=1),
    current_user: Account = Depends(get_current_user),
):
    area = await Area.get(id=area_id)
    await area.update_from_dict(new_area.dict(exclude_unset=True))
    await area.save()
    return await AreaOut.from_tortoise_orm(area)


@router.delete("/{area_id}")
@login_required(AccountRole.ADMIN)
async def delete_area(
    area_id: int = Path(ge=1),
    current_user: Account = Depends(get_current_user),
):
    area = await Area.get(id=area_id)
    await area.delete()
