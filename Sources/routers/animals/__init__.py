from datetime import datetime, timezone

from fastapi import APIRouter, Query, Depends, Path, HTTPException, status

from models.orm import (
    Animal,
    AnimalLifeStatus,
    Account,
    Location,
    AnimalType,
    AccountRole,
)
from models.pydantic import AnimalOut, UpdateAnimal, AnimalIn
from routers.users.utils import get_current_user, login_required
from routers.animals import locations, all_types, animal_types

router = APIRouter(prefix="/animals")
router.include_router(locations.router)
router.include_router(all_types.router)
router.include_router(animal_types.router)


@router.get("/search", response_model=list[AnimalOut])
@login_required()
async def search_animals(
    current_user: Account | None = Depends(get_current_user),
    start_date_time: datetime = Query(default=None, alias="startDateTime"),
    end_date_time: datetime = Query(default=None, alias="endDateTime"),
    chipper_id: int = Query(default=None, alias="chipperId"),
    chipping_location_id: int = Query(default=None, alias="chippingLocationId"),
    life_status: AnimalLifeStatus = Query(default=None, alias="lifeStatus"),
    gender: str = Query(default=None, alias="gender"),
    from_: int = Query(default=0, ge=0, alias="from"),
    size: int = Query(default=10, ge=1),
):
    query = Animal.all()
    if start_date_time is not None:
        query = query.filter(chipping_date_time__gte=start_date_time)
    if end_date_time is not None:
        query = query.filter(chipping_date_time__lte=end_date_time)
    if chipper_id is not None:
        query = query.filter(chipper__id=chipper_id)
    if chipping_location_id is not None:
        query = query.filter(chipping_location__id=chipping_location_id)
    if life_status is not None:
        query = query.filter(life_status=life_status)
    if gender is not None:
        query = query.filter(gender=gender)

    return [
        await AnimalOut.from_orm(e)
        for e in await query.order_by("id").offset(from_).limit(size)
    ]


@router.get("/{animal_id}", response_model=AnimalOut)
@login_required()
async def get_animal(
    animal_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    animal = await Animal.get(id=animal_id)
    return await AnimalOut.from_orm(animal)


@router.put("/{animal_id}", response_model=AnimalOut)
@login_required(AccountRole.CHIPPER)
async def update_animal(
    new_animal: UpdateAnimal,
    animal_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    animal = await Animal.get(id=animal_id)
    await animal.fetch_related("visited_locations")

    if (
        animal.life_status == AnimalLifeStatus.DEAD
        and new_animal.life_status == AnimalLifeStatus.ALIVE
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="animal is dead"
        )

    if (
        len(animal.visited_locations) > 0
        and animal.visited_locations[0].location_point_id
        == new_animal.chipping_location_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="has same chipping location"
        )

    await Location.get(id=new_animal.chipping_location_id)  # check if location exists
    await Account.get(id=new_animal.chipper_id)  # check if account exists
    await animal.update_from_dict(new_animal.dict(exclude_unset=True))

    if animal.life_status == AnimalLifeStatus.DEAD and animal.death_date_time is None:
        animal.death_date_time = datetime.now(tz=timezone.utc)

    await animal.save()
    return await AnimalOut.from_orm(animal)


@router.post("", response_model=AnimalOut, status_code=status.HTTP_201_CREATED)
@login_required(AccountRole.CHIPPER)
async def create_animal(
    animal: AnimalIn, current_user: Account | None = Depends(get_current_user)
):
    type_ids = animal.animal_types
    data = animal.dict(exclude_unset=True)
    del data["animal_types"]
    data["chipper"] = await Account.get(id=animal.chipper_id)
    data["chipper_location"] = await Location.get(id=animal.chipping_location_id)
    types = [await AnimalType.get(id=type_id) for type_id in type_ids]
    saved_animal = await Animal.create(**data)
    await saved_animal.animal_types.add(*types)

    return await AnimalOut.from_orm(saved_animal)


@router.delete("/{animal_id}")
@login_required(AccountRole.ADMIN)
async def delete_animal(
    animal_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    animal = await Animal.get(id=animal_id)
    await animal.fetch_related("visited_locations")
    if len(animal.visited_locations) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    await animal.delete()
