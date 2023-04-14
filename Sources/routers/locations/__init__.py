from fastapi import APIRouter, Path, Depends, status, HTTPException

from models.orm import Account, Location, AnimalVisitedLocation, AccountRole
from models.pydantic import LocationOut, LocationIn
from routers.users.utils import get_current_user, login_required
from routers.locations import geohash

router = APIRouter(prefix="/locations")
router.include_router(geohash.router)


@router.get("", response_model=int)
@login_required()
async def get_location_id(
    location: LocationIn = Depends(geohash.valid_location),
    current_user: Account | None = Depends(get_current_user),
):
    location = await Location.get(latitude=location.latitude, longitude=location.longitude)
    return location.id


@router.get("/{location_id}", response_model=LocationOut)
@login_required()
async def get_location(
    location_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    return await LocationOut.from_queryset_single(Location.get(id=location_id))


@router.post("", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
@login_required(AccountRole.CHIPPER)
async def create_location(
    location: LocationIn,
    current_user: Account | None = Depends(get_current_user),
):
    return await LocationOut.from_tortoise_orm(
        await Location.create(**location.dict(exclude_unset=True))
    )


@router.delete("/{location_id}")
@login_required(AccountRole.ADMIN)
async def delete_location(
    location_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    location = await Location.get(id=location_id)
    await location.fetch_related("chipped_animals")
    if len(location.chipped_animals) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    visited_by = await AnimalVisitedLocation.filter(location_point_id=location_id)
    if len(visited_by) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    await location.delete()


@router.put("/{location_id}", response_model=LocationOut)
@login_required(AccountRole.CHIPPER)
async def update_location(
    new_location: LocationIn,
    location_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    location = await Location.get(id=location_id)
    await location.update_from_dict(new_location.dict(exclude_unset=True))
    await location.save()
    return location
