from tortoise import fields, models, validators
from tortoise.contrib.pydantic import pydantic_model_creator
from constants import EMAIL_REGEX
import enum


class Account(models.Model):
    id = fields.IntField(pk=True)

    first_name = fields.CharField(max_length=255)
    last_name = fields.CharField(max_length=255)
    email = fields.CharField(
        max_length=255, validators=[validators.RegexValidator(EMAIL_REGEX, flags=0)]
    )
    password_hash = fields.CharField(max_length=128)

    class PydanticMeta:
        exclude = ["password_hash"]


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


class AnimalType(models.Model):
    id = fields.IntField(pk=True)
    type = fields.CharField(max_length=255, unique=True)


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
    visited_locations = fields.ManyToManyField("models.Location", on_delete=fields.RESTRICT)
    animal_types = fields.ManyToManyField("models.AnimalType", on_delete=fields.RESTRICT)
    life_status = fields.CharEnumField(AnimalLifeStatus)
    gender = fields.CharEnumField(AnimalGender)
    chipping_date_time = fields.DatetimeField(auto_now_add=True)
    chipper_id = fields.ForeignKeyField("models.Account", on_delete=fields.RESTRICT)
    chipping_location_id = fields.ForeignKeyField("models.Location", on_delete=fields.RESTRICT)
    death_date_time = fields.DatetimeField(null=True)


Account_Pydantic = pydantic_model_creator(Account, name="Account")
AccountIn_Pydantic = pydantic_model_creator(Account, name="AccountIn", exclude_readonly=True)
