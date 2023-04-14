from pygeohash import encode
from fastapi import APIRouter, Query, Depends, Response
from base64 import b64encode
from hashlib import md5

from models.orm import Account
from models.pydantic import LocationIn
from routers.users.utils import login_required, get_current_user


def geohash_v1(location: LocationIn) -> str:
    return encode(location.latitude, location.longitude)


def geohash_v2(location: LocationIn) -> str:
    v1 = geohash_v1(location)
    return b64encode(v1.encode()).decode()


def geohash_v3(location: LocationIn) -> str:
    v1 = geohash_v1(location)
    hashed: bytes = md5(v1.encode()).digest()
    reversed_hash = hashed[::-1]
    return b64encode(reversed_hash).decode()


def as_plain_text(text: str) -> Response:
    return Response(text, media_type="text/plain")


def valid_location(latitude: float = Query(), longitude: float = Query()) -> LocationIn:
    return LocationIn(
        latitude=latitude,
        longitude=longitude
    )


router = APIRouter()

@router.get("/geohash")
@login_required()
async def get_geohash_v1(
    location: LocationIn = Depends(valid_location),
    current_user: Account | None = Depends(get_current_user),
):
    return as_plain_text(geohash_v1(location))


@router.get("/geohashv2")
@login_required()
async def get_geohash_v2(
    location: LocationIn = Depends(valid_location),
    current_user: Account | None = Depends(get_current_user),
):
    return as_plain_text(geohash_v2(location))


@router.get("/geohashv3")
@login_required()
async def get_geohash_v2(
    location: LocationIn = Depends(valid_location),
    current_user: Account | None = Depends(get_current_user),
):
    return as_plain_text(geohash_v3(location))
