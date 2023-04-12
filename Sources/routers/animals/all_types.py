from fastapi import APIRouter, status, Path, Depends, HTTPException

from models.orm import Account, AnimalType, AccountRole
from models.pydantic import AnimalTypeOut, AnimalTypeIn
from routers.users.utils import get_current_user, login_required

router = APIRouter(prefix="/types")


@router.get("/{animal_type_id}", response_model=AnimalTypeOut)
@login_required()
async def get_animal_types(
    animal_type_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    return await AnimalTypeOut.from_queryset_single(AnimalType.get(id=animal_type_id))


@router.post(
    "",
    response_model=AnimalTypeOut,
    status_code=status.HTTP_201_CREATED,
)
@login_required(AccountRole.CHIPPER)
async def create_animal_type(
    animal_type: AnimalTypeIn,
    current_user: Account | None = Depends(get_current_user),
):
    return await AnimalTypeOut.from_tortoise_orm(
        await AnimalType.create(**animal_type.dict(exclude_unset=True))
    )


@router.put("/{animal_type_id}", response_model=AnimalTypeOut)
@login_required(AccountRole.CHIPPER)
async def update_assigned_animal_type(
    new_type: AnimalTypeIn,
    animal_type_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    animal_type = await AnimalType.get(id=animal_type_id)
    await animal_type.update_from_dict(new_type.dict(exclude_unset=True))
    await animal_type.save()
    return animal_type


@router.delete("/{animal_type_id}")
@login_required(AccountRole.ADMIN)
async def delete_animal_type(
    animal_type_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    animal_type = await AnimalType.get(id=animal_type_id)
    await animal_type.fetch_related("animals")
    if len(animal_type.animals) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    await animal_type.delete()
