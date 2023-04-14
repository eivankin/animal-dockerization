from datetime import date

from fastapi import APIRouter, Path, Depends, Query
from shapely import Point, Polygon
from tortoise.expressions import Q

from models.orm import (
    Area,
    Account,
    AnimalVisitedLocation,
    Animal,
    AnimalType,
    Location,
)
from models.pydantic import (
    AreaAnalytics,
    AnimalTypeAnalytics,
    VisitedLocationInfo,
)
from routers.users.utils import get_current_user, login_required

router = APIRouter(prefix="/{area_id}/analytics")


def add_type_stats(
    type_to_analytics: dict[int, AnimalTypeAnalytics], current_animal_type: AnimalType
) -> None:
    type_to_analytics[current_animal_type.id] = type_to_analytics.get(
        current_animal_type.id,
        AnimalTypeAnalytics(
            animal_type=current_animal_type.type,
            animal_type_id=current_animal_type.id,
        ),
    )


async def get_all_visits_and_locations(
    end_date: date | None, area: Polygon
) -> tuple[set[int], set[int]]:
    all_visits = AnimalVisitedLocation.all()
    all_locations = Location.all()
    if end_date is not None:
        all_visits = all_visits.filter(date_time_of_visit_location_point__lte=end_date)
    locations_in_area: set[int] = {
        loc.id
        for loc in await all_locations
        if Point(loc.latitude, loc.longitude).intersects(area)
    }
    visits: set[int] = {
        v.id for v in await all_visits if v.location_point_id in locations_in_area
    }
    return visits, locations_in_area


async def get_visited_locations_info(
    animal: Animal,
    start_date: date | None,
    end_date: date | None,
    locations_in_area: set[int],
) -> list[VisitedLocationInfo]:
    visited_locations = animal.visited_locations.all()
    if end_date is not None:
        visited_locations = visited_locations.filter(
            date_time_of_visit_location_point__lte=end_date
        )

    visited_locations_info: list[VisitedLocationInfo] = [
        VisitedLocationInfo(
            is_in_dates=v.date_time_of_visit_location_point.date() > start_date
            if start_date
            else True,
            is_in_area=v.location_point_id in locations_in_area,
        )
        for v in await visited_locations.order_by("date_time_of_visit_location_point")
    ]
    visited_locations_info.insert(
        0,
        VisitedLocationInfo(
            is_in_dates=animal.chipping_date_time.date() > start_date
            if start_date
            else True,
            is_in_area=animal.chipping_location_id in locations_in_area,
        ),
    )
    return visited_locations_info


def get_analytics(
    visited_locations_info: list[VisitedLocationInfo],
) -> tuple[bool, bool, bool]:
    is_in_area = visited_locations_info[0].is_in_area
    is_arrived = False
    is_gone = False
    for fst, snd in zip(visited_locations_info, visited_locations_info[1:]):
        if snd.is_in_area:
            is_in_area = True
            if snd.is_in_dates:
                is_arrived = True
        else:
            is_in_area = False
            if snd.is_in_dates and fst.is_in_area:
                is_gone = True
    return is_in_area, is_arrived, is_gone


@router.get("", response_model=AreaAnalytics)
@login_required()
async def get_area_analytics(
    area_id: int = Path(ge=1),
    start_date: date | None = Query(default=None, alias="startDate"),
    end_date: date | None = Query(default=None, alias="endDate"),
    current_user: Account | None = Depends(get_current_user),
):
    type_to_analytics: dict[int, AnimalTypeAnalytics] = {}
    analytics = AreaAnalytics()

    area = await Area.get(id=area_id)

    visits, locations_in_area = await get_all_visits_and_locations(end_date, area.area_points)
    animals_in_area = await Animal.filter(
        Q(visited_locations__id__in=visits)
        | Q(chipping_location_id__in=locations_in_area)
    ).distinct()
    for animal in animals_in_area:
        await animal.fetch_related("animal_types", "chipping_location")
        visited_locations_info = await get_visited_locations_info(
            animal, start_date, end_date, locations_in_area
        )

        is_in_area, is_arrived, is_gone = get_analytics(visited_locations_info)

        analytics.total_quantity_animals += is_in_area
        analytics.total_animals_arrived += is_arrived
        analytics.total_animals_gone += is_gone
        for animal_type in animal.animal_types:
            add_type_stats(type_to_analytics, animal_type)
            type_to_analytics[animal_type.id].quantity_animals += is_in_area
            type_to_analytics[animal_type.id].animals_arrived += is_arrived
            type_to_analytics[animal_type.id].animals_gone += is_gone

    analytics.animals_analytics = [a for a in type_to_analytics.values()]
    return analytics
