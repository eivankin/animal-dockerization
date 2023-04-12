import enum

from tortoise import models, fields, validators

NON_BLANK_REGEX = r"[^\s]"

NON_BLANK_VALIDATORS = [
    validators.MinLengthValidator(1),
    validators.RegexValidator(NON_BLANK_REGEX, flags=0),
]


class AccountRole(enum.StrEnum):
    """Порядок перечисления прав используется для сравнения ролей"""

    ADMIN = "ADMIN"  # Наибольшие права доступа
    CHIPPER = "CHIPPER"
    USER = "USER"  # Наименьшие права доступа

    @classmethod
    def __get_val_idx(cls, value):
        return list(cls).index(value)

    def __lt__(self, other):
        """Чем выше (ближе к старту списка) роль, тем больше у неё прав"""
        self_idx = self.__get_val_idx(self)
        other_idx = self.__get_val_idx(other)
        return self_idx > other_idx


class Account(models.Model):
    id = fields.IntField(pk=True)

    first_name = fields.CharField(max_length=255, validators=NON_BLANK_VALIDATORS)
    last_name = fields.CharField(max_length=255, validators=NON_BLANK_VALIDATORS)
    email = fields.CharField(
        max_length=255,
        unique=True,
    )
    password_hash = fields.CharField(max_length=128)
    role = fields.CharEnumField(AccountRole, default=AccountRole.USER)

    class PydanticMeta:
        exclude = ["password_hash"]


class AnimalVisitedLocation(models.Model):
    id = fields.IntField(pk=True)
    animal = fields.ForeignKeyField(
        "models.Animal",
        on_delete=fields.CASCADE,
        related_name="visited_locations",
    )
    location_point = fields.ForeignKeyField(
        "models.Location", on_delete=fields.RESTRICT
    )
    date_time_of_visit_location_point = fields.DatetimeField(auto_now_add=True)

    class PydanticMeta:
        exclude = ("animal",)

    class Meta:
        table = "animal_visited_location"


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
    visited_locations: fields.ForeignKeyRelation
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


class Location(models.Model):
    id = fields.IntField(pk=True)

    # Широта
    latitude = fields.FloatField(
        validators=[
            validators.MaxValueValidator(90),
            validators.MinValueValidator(-90),
        ],
    )

    # Долгота
    longitude = fields.FloatField(
        validators=[
            validators.MaxValueValidator(180),
            validators.MinValueValidator(-180),
        ],
    )
    chipped_animals: fields.ForeignKeyRelation[Animal]

    class Meta:
        unique_together = (("latitude", "longitude"),)


class AnimalType(models.Model):
    id = fields.IntField(pk=True)
    type = fields.CharField(
        max_length=255, unique=True, validators=NON_BLANK_VALIDATORS
    )
    animals: fields.ManyToManyRelation[Animal]
