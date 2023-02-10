import pydantic
from tortoise import fields, models, validators
from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import BaseConfig, BaseModel, EmailStr
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


AnimalType_Pydantic = pydantic_model_creator(
    AnimalType, name="AnimalType", config_class=CamelCaseConfig
)

AnimalTypeIn_Pydantic = pydantic_model_creator(
    AnimalType, name="AnimalTypeIn", config_class=CamelCaseConfig, exclude_readonly=True
)


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
        "models.Location", on_delete=fields.RESTRICT
    )
    animal_types = fields.ManyToManyField(
        "models.AnimalType", on_delete=fields.RESTRICT
    )
    life_status = fields.CharEnumField(AnimalLifeStatus)
    gender = fields.CharEnumField(AnimalGender)
    chipping_date_time = fields.DatetimeField(auto_now_add=True)
    chipper_id = fields.ForeignKeyField("models.Account", on_delete=fields.RESTRICT)
    chipping_location_id = fields.ForeignKeyField(
        "models.Location", on_delete=fields.RESTRICT, related_name=False
    )
    death_date_time = fields.DatetimeField(null=True)


Animal_Pydantic = pydantic_model_creator(
    Animal, name="Animal", config_class=CamelCaseConfig
)
AnimalIn_Pydantic = pydantic_model_creator(
    Animal, name="AnimalIn", config_class=CamelCaseConfig, exclude_readonly=True
)
