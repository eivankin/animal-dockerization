from datetime import datetime, timezone
from tortoise.exceptions import IntegrityError

import pydantic
import tortoise
from fastapi.exceptions import RequestValidationError
from passlib.context import CryptContext
from tortoise.contrib.fastapi import register_tortoise
from fastapi import FastAPI, Depends, status, HTTPException, Query, Path
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import PlainTextResponse

from constants import DB_URL, DEBUG
from models import (
    Account,
    Account_Pydantic,
    AccountIn,
    Animal,
    AnimalOut,
    AnimalIn,
    Location_Pydantic,
    Location,
    LocationIn_Pydantic,
    AnimalType,
    AnimalType_Pydantic,
    AnimalTypeIn_Pydantic,
    AnimalLifeStatus,
    UpdateAnimalType,
    AnimalVisitedLocation,
    UpdateVisitedLocation,
    VisitedLocationOut,
    AnimalUpdate,
)

app = FastAPI(debug=DEBUG)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBasic(auto_error=False)


def login_required(user: Account | None) -> None:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


@app.exception_handler(tortoise.exceptions.IntegrityError)
async def integrity_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=status.HTTP_409_CONFLICT)


@app.exception_handler(tortoise.exceptions.DoesNotExist)
async def not_found_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=status.HTTP_404_NOT_FOUND)


@app.exception_handler(RequestValidationError)
@app.exception_handler(pydantic.error_wrappers.ValidationError)
@app.exception_handler(tortoise.exceptions.ValidationError)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=status.HTTP_400_BAD_REQUEST)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_current_user(
    credentials: HTTPBasicCredentials = Depends(security),
) -> Account | None:
    if credentials is None:
        return None

    email = credentials.username
    user = await Account.get_or_none(email=email)
    if user is not None and verify_password(credentials.password, user.password_hash):
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@app.get("/accounts/search", response_model=list[Account_Pydantic])
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

    return await Account_Pydantic.from_queryset(
        query.order_by("id").offset(from_).limit(size)
    )


@app.get("/accounts/{account_id}", response_model=Account_Pydantic)
async def get_account(
    account_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    return await Account_Pydantic.from_queryset_single(Account.get(id=account_id))


@app.put("/accounts/{account_id}", response_model=Account_Pydantic)
async def update_account(
    new_account: AccountIn,
    account_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    if current_user.id != account_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    account = await Account.get(id=account_id)
    await account.update_from_dict(new_account.dict())
    pwd_hash = get_password_hash(new_account.password)
    account.password_hash = pwd_hash
    await account.save()
    return account


@app.delete("/accounts/{account_id}")
async def delete_account(
    account_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    if current_user.id != account_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    account = await Account.get(id=account_id)
    try:
        await account.delete()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)


@app.post(
    "/registration",
    response_model=Account_Pydantic,
    status_code=status.HTTP_201_CREATED,
)
async def create_account(
    account: AccountIn, current_user: Account | None = Depends(get_current_user)
):
    if current_user is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    pwd_hash = get_password_hash(account.password)
    return await Account_Pydantic.from_tortoise_orm(
        await Account.create(**account.dict(), password_hash=pwd_hash)
    )


@app.get("/animals/search", response_model=list[AnimalOut])
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


@app.get("/animals/{animal_id}", response_model=AnimalOut)
async def get_animal(
    animal_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    animal = await Animal.get(id=animal_id)
    return await AnimalOut.from_orm(animal)


@app.put("/animals/{animal_id}", response_model=AnimalOut)
async def update_animal(
    new_animal: AnimalUpdate,
    animal_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
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
        and animal.visited_locations[0].id == new_animal.chipping_location_id
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


@app.post("/animals", response_model=AnimalOut, status_code=status.HTTP_201_CREATED)
async def create_animal(
    animal: AnimalIn, current_user: Account | None = Depends(get_current_user)
):

    login_required(current_user)
    type_ids = animal.animal_types
    data = animal.dict(exclude_unset=True)
    del data["animal_types"]
    data["chipper"] = await Account.get(id=animal.chipper_id)
    data["chipper_location"] = await Location.get(id=animal.chipping_location_id)
    saved_animal = await Animal.create(**data)
    await saved_animal.animal_types.add(
        *[await AnimalType.get(id=type_id) for type_id in type_ids]
    )

    return await AnimalOut.from_orm(saved_animal)


@app.delete("/animals/{animal_id}")
async def delete_animal(
    animal_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)

    animal = await Animal.get(id=animal_id)
    await animal.fetch_related("visited_locations")
    if len(animal.visited_locations) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    await animal.delete()


@app.get("/locations/{location_id}", response_model=Location_Pydantic)
async def get_location(
    location_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    return await Location_Pydantic.from_queryset_single(Location.get(id=location_id))


@app.post(
    "/locations", response_model=Location_Pydantic, status_code=status.HTTP_201_CREATED
)
async def create_location(
    location: LocationIn_Pydantic,
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    return await Location_Pydantic.from_tortoise_orm(
        await Location.create(**location.dict(exclude_unset=True))
    )


@app.delete("/locations/{location_id}")
async def delete_location(
    location_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    location = await Location.get(id=location_id)
    await location.fetch_related("chipped_animals", "visited_by")
    if len(location.chipped_animals) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    if len(location.visited_by) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    await location.delete()


@app.put("/locations/{location_id}", response_model=Location_Pydantic)
async def update_location(
    new_location: LocationIn_Pydantic,
    location_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    location = await Location.get(id=location_id)
    await location.update_from_dict(new_location.dict(exclude_unset=True))
    await location.save()
    return location


@app.get("/animals/types/{animal_type_id}", response_model=AnimalType_Pydantic)
async def get_animal_types(
    animal_type_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    return await AnimalType_Pydantic.from_queryset_single(
        AnimalType.get(id=animal_type_id)
    )


@app.post(
    "/animals/{animal_id}/types/{type_id}",
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


@app.put("/animals/{animal_id}/types", response_model=AnimalOut)
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


@app.delete("/animals/{animal_id}/types/{type_id}")
async def delete_animal_type_relation(
    animal_id: int = Path(ge=1),
    type_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    animal = await Animal.get(id=animal_id)
    await animal.fetch_related("animal_types")
    type_to_remove = await animal.animal_types.all().get(id=type_id)
    if len(animal.animal_types) == 1 and animal.animal_types[0] == type_to_remove:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    await animal.animal_types.remove(type_to_remove)
    return await AnimalOut.from_orm(animal)


@app.post(
    "/animals/types",
    response_model=AnimalType_Pydantic,
    status_code=status.HTTP_201_CREATED,
)
async def create_animal_type(
    animal_type: AnimalTypeIn_Pydantic,
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    return await AnimalType_Pydantic.from_tortoise_orm(
        await AnimalType.create(**animal_type.dict(exclude_unset=True))
    )


@app.put("/animals/types/{animal_type_id}", response_model=AnimalType_Pydantic)
async def update_assigned_animal_type(
    new_type: AnimalTypeIn_Pydantic,
    animal_type_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    animal_type = await AnimalType.get(id=animal_type_id)
    await animal_type.update_from_dict(new_type.dict(exclude_unset=True))
    await animal_type.save()
    return animal_type


@app.delete("/animals/types/{animal_type_id}")
async def delete_animal_type(
    animal_type_id: int = Path(ge=1),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    animal_type = await AnimalType.get(id=animal_type_id)
    await animal_type.fetch_related("animals")
    if len(animal_type.animals) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    await animal_type.delete()


@app.get("/animals/{animal_id}/locations", response_model=list[VisitedLocationOut])
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
    query = animal.visited_locations_junction.all()
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


@app.post(
    "/animals/{animal_id}/locations/{location_id}",
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
    if len(animal.visited_locations) == 0 \
            and location.id == animal.chipping_location_id:  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="repeating chipping location",
        )

    if (
        len(animal.visited_locations) > 0
        and location_id == animal.visited_locations[-1].id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="repeating location"
        )

    await animal.visited_locations.add(location)
    return VisitedLocationOut.from_orm(
        await animal.visited_locations_junction.all().get(location_point_id=location_id)
    )


@app.delete("/animals/{animal_id}/locations/{location_id}")
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
    if (
        len(animal.visited_locations) >= 2
        and location.location_point_id == animal.visited_locations[0].id  # type: ignore
        and animal.chipping_location_id == animal.visited_locations[1].id  # type: ignore
    ):
        await animal.visited_locations.remove(await animal.chipping_location)
    # else:  # uncomment to pass all tests
    await animal.visited_locations.remove(await location.location_point)


@app.put("/animals/{animal_id}/locations", response_model=VisitedLocationOut)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="same location")

    if visited_location.animal_id != animal_id:  # type: ignore
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if visited_location.location_point == new_location:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    sorted_locations = await animal.visited_locations_junction.order_by(
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


register_tortoise(
    app=app,
    db_url=DB_URL,
    modules={"models": ["models"]},
    generate_schemas=True,
)
