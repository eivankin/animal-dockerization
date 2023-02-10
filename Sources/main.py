import pydantic
import tortoise
from fastapi.exceptions import RequestValidationError
from passlib.context import CryptContext
from tortoise.contrib.fastapi import register_tortoise
from fastapi import FastAPI, Depends, status, HTTPException, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import PlainTextResponse

from constants import DB_URL, DEBUG
from models import (
    Account,
    Account_Pydantic,
    AccountIn,
    Animal,
    Animal_Pydantic,
    AnimalIn_Pydantic,
    Location_Pydantic,
    Location,
    LocationIn_Pydantic,
    AnimalType,
    AnimalType_Pydantic, AnimalTypeIn_Pydantic,
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
    return PlainTextResponse(str(exc), status_code=409)


@app.exception_handler(tortoise.exceptions.DoesNotExist)
async def not_found_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=404)


@app.exception_handler(RequestValidationError)
@app.exception_handler(pydantic.error_wrappers.ValidationError)
@app.exception_handler(tortoise.exceptions.ValidationError)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=400)


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


def validate_id(id_val: int) -> int:
    if id_val < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    return id_val


@app.get("/accounts/search", response_model=list[Account_Pydantic])
async def search_account(
    current_user: Account | None = Depends(get_current_user),
    first_name_like: str = Query(default="", alias="firstName"),
    last_name_like: str = Query(default="", alias="lastName"),
    email_like: str = Query(default="", alias="email"),
    from_: int = Query(default=0, ge=0, alias="from"),
    size: int = Query(default=10, ge=1),
):
    return await Account_Pydantic.from_queryset(
        Account.filter(
            first_name__icontains=first_name_like,
            last_name__icontains=last_name_like,
            email__icontains=email_like,
        )
        .offset(from_)
        .limit(size)
    )


@app.get("/accounts/{id_val}", response_model=Account_Pydantic)
async def get_account(
    account_id: int = Depends(validate_id),
    current_user: Account | None = Depends(get_current_user),
):
    return await Account_Pydantic.from_queryset_single(Account.get(id=account_id))


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


@app.get("/animals/search", response_model=list[Animal_Pydantic])
async def search_animals(
    current_user: Account | None = Depends(get_current_user),
    from_: int = Query(default=0, ge=0, alias="from"),
    size: int = Query(default=10, ge=1),
):
    # TODO
    return await Animal_Pydantic.from_queryset(Animal.all().offset(from_).limit(size))


@app.get("/animals/{id_val}", response_model=Animal_Pydantic)
async def get_animal(
    animal_id: int = Depends(validate_id),
    current_user: Account | None = Depends(get_current_user),
):
    return await Animal_Pydantic.from_queryset_single(Animal.get(id=animal_id))


@app.post(
    "/animals", response_model=Animal_Pydantic, status_code=status.HTTP_201_CREATED
)
async def create_animal(
    animal: AnimalIn_Pydantic, current_user: Account | None = Depends(get_current_user)
):
    # TODO
    login_required(current_user)
    return await Animal_Pydantic.from_tortoise_orm(
        await Animal.create(**animal.dict(exclude_unset=True))
    )


@app.get("/locations/{id_val}", response_model=Location_Pydantic)
async def get_location(
    location_id: int = Depends(validate_id),
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


@app.delete("/locations/{id_val}")
async def delete_location(
    location_id: int = Depends(validate_id),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    location = await Location.get(id=location_id)
    await location.delete()


@app.put("/locations/{id_val}", response_model=Location_Pydantic)
async def update_location(
    new_location: LocationIn_Pydantic,
    location_id: int = Depends(validate_id),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    location = await Location.get(id=location_id)
    await location.update_from_dict(new_location.dict(exclude_unset=True))
    await location.save()
    return location


@app.get("/animals/types/{id_val}", response_model=AnimalType_Pydantic)
async def get_animal_type(
    animal_type_id: int = Depends(validate_id),
    current_user: Account | None = Depends(get_current_user),
):
    return await AnimalType_Pydantic.from_queryset_single(
        AnimalType.get(id=animal_type_id)
    )


@app.post("/animals/types", response_model=AnimalType_Pydantic, status_code=status.HTTP_201_CREATED)
async def create_animal_type(
    animal_type: AnimalTypeIn_Pydantic,
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    return await AnimalType_Pydantic.from_tortoise_orm(
        await AnimalType.create(**animal_type.dict(exclude_unset=True))
    )


@app.put("/animals/types/{id_val}", response_model=AnimalType_Pydantic)
async def update_animal_type(
    new_type: AnimalTypeIn_Pydantic,
    animal_type_id: int = Depends(validate_id),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    animal_type = await AnimalType.get(id=animal_type_id)
    await animal_type.update_from_dict(new_type.dict(exclude_unset=True))
    await animal_type.save()
    return animal_type


@app.delete("/animals/types/{id_val}")
async def delete_animal_type(
    animal_type_id: int = Depends(validate_id),
    current_user: Account | None = Depends(get_current_user),
):
    login_required(current_user)
    animal_type = await AnimalType.get(id=animal_type_id)
    await animal_type.delete()


@app.get("/animals/{id_val}/locations", response_model=list[Location_Pydantic])
async def get_animal_locations(
    animal_id: int = Depends(validate_id),
    current_user: Account | None = Depends(get_current_user),
):
    animal = await Animal.get(id=animal_id)
    return await Location_Pydantic.from_queryset(animal.visited_locations)


register_tortoise(
    app=app,
    db_url=DB_URL,
    modules={"models": ["models"]},
    generate_schemas=True,
)
