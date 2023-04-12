from fastapi import APIRouter, status, Path, Depends, HTTPException

from models.orm import Account, Animal, AnimalType
from models.pydantic import AnimalOut, UpdateAnimalType
from routers.users.utils import get_current_user, login_required

router = APIRouter(prefix="/{animal_id}/types")


@router.post(
    "/{type_id}",
    response_model=AnimalOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_animal_type(
    animal_id: int = Path(ge=1),
    type_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    animal = await Animal.get(id=animal_id)
    await animal.animal_types.add(await AnimalType.get(id=type_id))
    return await AnimalOut.from_orm(animal)


@router.put("", response_model=AnimalOut)
async def update_animal_type(
    update_type: UpdateAnimalType,
    animal_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    animal = await Animal.get(id=animal_id)
    await animal.fetch_related("animal_types")
    new_type = await AnimalType.get(id=update_type.new_type_id)
    old_type = await animal.animal_types.all().get(id=update_type.old_type_id)
    if new_type in animal.animal_types:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    await animal.animal_types.remove(old_type)
    await animal.animal_types.add(new_type)

    return await AnimalOut.from_orm(animal)


@router.delete("/{type_id}")
async def delete_animal_type_relation(
    animal_id: int = Path(ge=1),
    type_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    animal = await Animal.get(id=animal_id)
    await animal.fetch_related("animal_types")
    type_to_remove = await animal.animal_types.all().get(id=type_id)
    if len(animal.animal_types) == 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    await animal.animal_types.remove(type_to_remove)
    return await AnimalOut.from_orm(animal)
