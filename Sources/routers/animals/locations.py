from datetime import datetime

from fastapi import APIRouter, status, Path, Query, Depends, HTTPException

from models.orm import (
    Account,
    Animal,
    AnimalLifeStatus,
    Location,
    AnimalVisitedLocation,
)
from models.pydantic import VisitedLocationOut, UpdateVisitedLocation
from routers.users.utils import get_current_user, login_required

router = APIRouter(prefix="/{animal_id}/locations")


@router.get("", response_model=list[VisitedLocationOut])
async def get_animal_locations(
    animal_id: int = Path(ge=1),
    start_date_time: datetime = Query(default=None, alias="startDateTime"),
    end_date_time: datetime = Query(default=None, alias="endDateTime"),
    from_: int = Query(default=0, alias="from", ge=0),
    size: int = Query(default=10, alias="size", ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    animal = await Animal.get(id=animal_id)
    await animal.fetch_related("visited_locations")
    query = animal.visited_locations.all()
    if start_date_time is not None:
        query = query.filter(date_time_of_visit_location_point__gte=start_date_time)
    if end_date_time is not None:
        query = query.filter(date_time_of_visit_location_point__lte=end_date_time)

    return [
        VisitedLocationOut.from_orm(e)
        for e in await query.order_by("date_time_of_visit_location_point")
        .offset(from_)
        .limit(size)
    ]


@router.post(
    "/{location_id}",
    response_model=VisitedLocationOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_animal_location(
    animal_id: int = Path(ge=1),
    location_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    animal = await Animal.get(id=animal_id)
    if animal.life_status == AnimalLifeStatus.DEAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="animal is dead"
        )

    location = await Location.get(id=location_id)
    await animal.fetch_related("visited_locations")
    if (
        len(animal.visited_locations) == 0
        and location.id == animal.chipping_location_id  # type: ignore
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="repeating chipping location",
        )

    if (
        len(animal.visited_locations) > 0
        and location_id == animal.visited_locations[-1].location_point_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="repeating location"
        )

    visited_location = await AnimalVisitedLocation.create(
        animal=animal, location_point=location
    )
    return VisitedLocationOut.from_orm(await visited_location)


@router.delete("/{location_id}")
async def delete_animal_location(
    animal_id: int = Path(ge=1),
    location_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    animal = await Animal.get(id=animal_id)
    location = await AnimalVisitedLocation.get(id=location_id)
    if location.animal_id != animal_id:  # type: ignore
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await animal.fetch_related("visited_locations", "chipping_location")
    sorted_locations = await animal.visited_locations.all().order_by(
        "date_time_of_visit_location_point"
    )
    if (
        len(sorted_locations) >= 2
        and location_id == sorted_locations[0].id  # type: ignore
        and animal.chipping_location_id == sorted_locations[1].location_point_id  # type: ignore
    ):
        await sorted_locations[1].delete()
    await location.delete()


@router.put("", response_model=VisitedLocationOut)
async def update_animal_location(
    update_visited_location: UpdateVisitedLocation,
    animal_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    animal = await Animal.get(id=animal_id)
    await animal.fetch_related("visited_locations")
    new_location = await Location.get(id=update_visited_location.location_point_id)
    visited_location = await AnimalVisitedLocation.get(
        id=update_visited_location.visited_location_point_id
    )
    if new_location.id == visited_location.location_point_id:  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="same location"
        )

    if visited_location.animal_id != animal_id:  # type: ignore
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if visited_location.location_point == new_location:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    sorted_locations = await animal.visited_locations.order_by(
        "date_time_of_visit_location_point"
    )

    if (
        sorted_locations[0].id == visited_location.id
        and new_location.id == animal.chipping_location_id  # type: ignore
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    visited_index = sorted_locations.index(visited_location)
    if (
        visited_index > 0
        and sorted_locations[visited_index - 1].location_point_id == new_location.id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="repeating location with the previous one",
        )
    if (
        visited_index < len(sorted_locations) - 1
        and sorted_locations[visited_index + 1].location_point_id == new_location.id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="repeating location with the next one",
        )

    visited_location.location_point = new_location
    await visited_location.save()
    return VisitedLocationOut.from_orm(visited_location)
