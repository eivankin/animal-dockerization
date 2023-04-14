from datetime import date

from fastapi import APIRouter, Path, Depends, Query
from shapely import Point
from tortoise.expressions import Q

from models.orm import Area, Account, AnimalVisitedLocation, Animal, AnimalType, Location
from models.pydantic import AreaAnalytics, AnimalTypeAnalytics, LocationOut
from routers.users.utils import get_current_user, login_required

router = APIRouter(prefix="/{area_id}/analytics")


@router.get("", response_model=AreaAnalytics)
@login_required()
async def get_area_analytics(
    area_id: int = Path(ge=1),
    start_date: date = Query(default=None, alias="startDate"),
    end_date: date = Query(default=None, alias="endDate"),
    current_user: Account | None = Depends(get_current_user),
):
    def add_type_stats(current_animal_type: AnimalType) -> None:
        type_to_analytics[current_animal_type.id] = type_to_analytics.get(
            current_animal_type.id,
            AnimalTypeAnalytics(
                animal_type=current_animal_type.type,
                animal_type_id=current_animal_type.id,
            ),
        )

    type_to_analytics: dict[int, AnimalTypeAnalytics] = {}
    analytics = AreaAnalytics()

    area = await Area.get(id=area_id)
    all_visits = AnimalVisitedLocation.all()
    all_locations = Location.all()
    if end_date is not None:
        all_visits = all_visits.filter(
            date_time_of_visit_location_point__lte=end_date
        )

    locations_in_area = [
        loc.id
        for loc in await all_locations
        if Point(
            loc.latitude, loc.longitude
        ).intersects(area.area_points)
    ]
    visits = [
        v.id
        for v in await all_visits
        if v.location_point_id in locations_in_area
    ]
    animals_in_area = (await Animal.filter(
        Q(visited_locations__id__in=visits) |
        Q(chipping_location_id__in=locations_in_area)).distinct())
    for animal in animals_in_area:
        await animal.fetch_related("animal_types", "chipping_location")
        visited_locations = animal.visited_locations.all()
        if start_date is not None:
            visited_locations = visited_locations.filter(
                date_time_of_visit_location_point__gte=start_date
            )
        if end_date is not None:
            visited_locations = visited_locations.filter(
                date_time_of_visit_location_point__lte=end_date
            )

        visited_locations = [v.location_point_id for v in await visited_locations.order_by(
            "date_time_of_visit_location_point"
        )]

        if not visited_locations:
            analytics.total_quantity_animals += 1

            for animal_type in animal.animal_types:
                add_type_stats(animal_type)
                type_to_analytics[animal_type.id].quantity_animals += 1

        elif visited_locations[-1] in locations_in_area:
            analytics.total_animals_arrived += 1
            analytics.total_quantity_animals += 1
            for animal_type in animal.animal_types:
                add_type_stats(animal_type)
                type_to_analytics[animal_type.id].quantity_animals += 1
                type_to_analytics[animal_type.id].animals_arrived += 1
        else:
            last_prev_point = animal.chipping_location.id
            if start_date is not None and start_date > animal.chipping_date_time.date():
                pass
                # last_prev_point = animal.chipping_location.id

            if any(loc in locations_in_area for loc in visited_locations) or \
                    (last_prev_point in locations_in_area):
                analytics.total_animals_gone += 1
                for animal_type in animal.animal_types:
                    add_type_stats(animal_type)
                    type_to_analytics[animal_type.id].animals_gone += 1

    analytics.animals_analytics = [a for a in type_to_analytics.values()]
    return analytics
