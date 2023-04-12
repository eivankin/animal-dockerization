from datetime import datetime

import pydantic
from humps import camelize
from pydantic import BaseConfig, BaseModel, EmailStr, conlist, conint, confloat
from tortoise.contrib.pydantic import pydantic_model_creator

from abc import ABCMeta

from .orm import (
    Account,
    NON_BLANK_VALIDATORS,
    AnimalGender,
    AnimalLifeStatus,
    Location,
    AnimalType,
    Animal,
    AnimalVisitedLocation,
)


ObjectID = conint(gt=0)
PositiveFloat = confloat(gt=0)


class CamelCaseConfig(BaseConfig):
    allow_population_by_field_name = True
    alias_generator = camelize


class AbstractCamelCaseModel(BaseModel, metaclass=ABCMeta):
    class Config(CamelCaseConfig):
        orm_mode = True


AccountOut = pydantic_model_creator(
    Account, name="AccountOut", config_class=CamelCaseConfig
)


class AccountIn(AbstractCamelCaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

    @pydantic.validator("password")
    def validate_password(cls, v):
        for validator in NON_BLANK_VALIDATORS:
            validator(v)
        return v


class AnimalOut(AbstractCamelCaseModel):
    id: ObjectID
    animal_types: conlist(ObjectID, min_items=1)
    weight: PositiveFloat
    length: PositiveFloat
    height: PositiveFloat
    gender: AnimalGender
    chipper_id: ObjectID
    chipping_location_id: ObjectID
    death_date_time: datetime | None
    visited_locations: list[ObjectID]
    life_status: AnimalLifeStatus
    chipping_date_time: datetime

    @classmethod
    async def from_orm(cls, animal: Animal) -> "AnimalOut":
        await animal.fetch_related()
        return cls(
            id=animal.id,
            weight=animal.weight,
            height=animal.height,
            gender=animal.gender,
            animal_types=[t.id for t in await animal.animal_types],
            chipper_id=animal.chipper_id,  # type: ignore
            visited_locations=[
                lc.id for lc in await AnimalVisitedLocation.filter(animal_id=animal.id)
            ],
            chipping_location_id=animal.chipping_location_id,  # type: ignore
            death_date_time=animal.death_date_time,
            life_status=animal.life_status,
            length=animal.length,
            chipping_date_time=animal.chipping_date_time,
        )


class AnimalIn(AbstractCamelCaseModel):
    animal_types: conlist(ObjectID, min_items=1)
    weight: PositiveFloat
    length: PositiveFloat
    height: PositiveFloat
    gender: AnimalGender
    chipper_id: ObjectID
    chipping_location_id: ObjectID
    life_status: AnimalLifeStatus | None = None


class UpdateAnimal(AbstractCamelCaseModel):
    weight: PositiveFloat
    length: PositiveFloat
    height: PositiveFloat
    gender: AnimalGender
    life_status: AnimalLifeStatus
    chipper_id: ObjectID
    chipping_location_id: ObjectID


class UpdateAnimalType(AbstractCamelCaseModel):
    old_type_id: ObjectID
    new_type_id: ObjectID


class VisitedLocationOut(AbstractCamelCaseModel):
    id: ObjectID
    date_time_of_visit_location_point: datetime
    location_point_id: ObjectID


class UpdateVisitedLocation(AbstractCamelCaseModel):
    visited_location_point_id: ObjectID
    location_point_id: ObjectID


LocationOut = pydantic_model_creator(
    Location, name="LocationOut", config_class=CamelCaseConfig
)

LocationIn = pydantic_model_creator(
    Location, name="LocationIn", config_class=CamelCaseConfig, exclude_readonly=True
)

AnimalTypeOut = pydantic_model_creator(
    AnimalType, name="AnimalTypeOut", config_class=CamelCaseConfig
)
AnimalTypeIn = pydantic_model_creator(
    AnimalType, name="AnimalTypeIn", config_class=CamelCaseConfig, exclude_readonly=True
)
