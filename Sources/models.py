from datetime import datetime

import pydantic
from tortoise import fields, models, validators
from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import BaseConfig, BaseModel, EmailStr, ValidationError
from humps import camelize
from constants import NON_BLANK_REGEX
import enum

NON_BLANK_VALIDATORS = [
    validators.MinLengthValidator(1),
    validators.RegexValidator(NON_BLANK_REGEX, flags=0),
]


class CamelCaseConfig(BaseConfig):
    allow_population_by_field_name = True
    alias_generator = camelize


class Account(models.Model):
    id = fields.IntField(pk=True)

    first_name = fields.CharField(max_length=255, validators=NON_BLANK_VALIDATORS)
    last_name = fields.CharField(max_length=255, validators=NON_BLANK_VALIDATORS)
    email = fields.CharField(
        max_length=255,
        unique=True,
    )
    password_hash = fields.CharField(max_length=128)

    class PydanticMeta:
        exclude = ["password_hash"]


Account_Pydantic = pydantic_model_creator(
    Account, name="Account", config_class=CamelCaseConfig
)


class AccountIn(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

    class Config(CamelCaseConfig):
        orm_mode = True

    @pydantic.validator("password")
    def validate_password(cls, v):
        for validator in NON_BLANK_VALIDATORS:
            validator(v)
        return v


class AnimalLifeStatus(enum.StrEnum):
    ALIVE = "ALIVE"
    DEAD = "DEAD"


class AnimalGender(enum.StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class Animal(models.Model):
    id = fields.IntField(pk=True)

    weight = fields.FloatField()  # Масса в кг
    length = fields.FloatField()  # Длина в метрах
    height = fields.FloatField()  # Высота в метрах
    visited_locations = fields.ManyToManyField(
        "models.Location",
        on_delete=fields.RESTRICT,
        through="animal_visited_location",
        forward_key="location_point_id",
        related_name="visited_by",
    )
    animal_types = fields.ManyToManyField(
        "models.AnimalType", on_delete=fields.CASCADE, related_name="animals"
    )
    life_status = fields.CharEnumField(AnimalLifeStatus, default=AnimalLifeStatus.ALIVE)
    gender = fields.CharEnumField(AnimalGender)
    chipping_date_time = fields.DatetimeField(auto_now_add=True)
    chipper = fields.ForeignKeyField("models.Account", on_delete=fields.RESTRICT)
    chipping_location = fields.ForeignKeyField(
        "models.Location", on_delete=fields.CASCADE, related_name="chipped_animals"
    )
    death_date_time = fields.DatetimeField(null=True)


Animal_Pydantic = pydantic_model_creator(
    Animal, name="Animal", config_class=CamelCaseConfig
)


class AnimalOut(BaseModel):
    id: int
    animal_types: list[int]
    weight: float
    length: float
    height: float
    gender: AnimalGender
    chipper_id: int
    chipping_location_id: int
    death_date_time: datetime | None
    visited_locations: list[int]
    life_status: AnimalLifeStatus
    chipping_date_time: datetime
    animal_types: list[int]

    class Config(CamelCaseConfig):
        orm_mode = True

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
            visited_locations=[lc.id for lc in
                               await AnimalVisitedLocation.filter(animal_id=animal.id)],
            chipping_location_id=animal.chipping_location_id,  # type: ignore
            death_date_time=animal.death_date_time,
            life_status=animal.life_status,
            length=animal.length,
            chipping_date_time=animal.chipping_date_time,
        )


class AnimalIn(BaseModel):
    animal_types: list[int]
    weight: float
    length: float
    height: float
    gender: AnimalGender
    chipper_id: int
    chipping_location_id: int
    life_status: AnimalLifeStatus | None = None

    class Config(CamelCaseConfig):
        orm_mode = True

    @pydantic.validator("animal_types")
    def validate_animal_types(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValidationError("animal_types must not be empty")
        if any(t < 1 for t in v):
            raise ValidationError("each element of animal_types must be greater than 0")
        return v

    @pydantic.validator("weight", "length", "height")
    def validate_characteristics(cls, v: float) -> float:
        if v <= 0:
            raise ValidationError("weight, length and height must be greater than 0")
        return v

    @pydantic.validator("chipping_location_id", "chipper_id")
    def validate_chipping_location_id(cls, v: int) -> int:
        if v < 1:
            raise ValidationError("id must be greater than 0")
        return v


class AnimalUpdate(BaseModel):
    weight: float
    height: float
    length: float
    gender: AnimalGender
    life_status: AnimalLifeStatus
    chipper_id: int
    chipping_location_id: int

    class Config(CamelCaseConfig):
        pass


class UpdateAnimalType(BaseModel):
    old_type_id: int
    new_type_id: int

    class Config(CamelCaseConfig):
        pass

    @pydantic.validator("new_type_id", "old_type_id")
    def validate_new_type_id(cls, v: int) -> int:
        if v < 1:
            raise ValidationError("id must be greater than 0")
        return v


class AnimalVisitedLocation(models.Model):
    id = fields.IntField(pk=True)
    animal = fields.ForeignKeyField("models.Animal", on_delete=fields.CASCADE)
    location_point = fields.ForeignKeyField(
        "models.Location", on_delete=fields.RESTRICT
    )
    date_time_of_visit_location_point = fields.DatetimeField(auto_now_add=True)

    class PydanticMeta:
        exclude = ("animal",)

    class Meta:
        table = "animal_visited_location"


class VisitedLocationOut(BaseModel):
    id: int
    date_time_of_visit_location_point: datetime
    location_point_id: int

    class Config(CamelCaseConfig):
        orm_mode = True

    @pydantic.validator("location_point_id")
    def validate_location_point_id(cls, v: int) -> int:
        if v < 1:
            raise ValidationError("id must be greater than 0")
        return v


class UpdateVisitedLocation(BaseModel):
    visited_location_point_id: int
    location_point_id: int

    class Config(CamelCaseConfig):
        pass

    @pydantic.validator("visited_location_point_id", "location_point_id")
    def validate_id(cls, v: int) -> int:
        if v < 1:
            raise ValidationError("id must be greater than 0")
        return v


class Location(models.Model):
    id = fields.IntField(pk=True)

    # Широта
    latitude = fields.FloatField(
        validators=[
            validators.MaxValueValidator(90),
            validators.MinValueValidator(-90),
        ],
        unique=True,
    )

    # Долгота
    longitude = fields.FloatField(
        validators=[
            validators.MaxValueValidator(180),
            validators.MinValueValidator(-180),
        ],
        unique=True,
    )
    chipped_animals: fields.ForeignKeyRelation[Animal]
    visited_by: fields.ManyToManyRelation[Animal]


Location_Pydantic = pydantic_model_creator(
    Location, name="Location", config_class=CamelCaseConfig
)
LocationIn_Pydantic = pydantic_model_creator(
    Location, name="LocationIn", config_class=CamelCaseConfig, exclude_readonly=True
)


class AnimalType(models.Model):
    id = fields.IntField(pk=True)
    type = fields.CharField(
        max_length=255, unique=True, validators=NON_BLANK_VALIDATORS
    )
    animals: fields.ManyToManyRelation[Animal]


AnimalType_Pydantic = pydantic_model_creator(
    AnimalType, name="AnimalType", config_class=CamelCaseConfig
)

AnimalTypeIn_Pydantic = pydantic_model_creator(
    AnimalType, name="AnimalTypeIn", config_class=CamelCaseConfig, exclude_readonly=True
)
