from fastapi import APIRouter

from routers import animals, users, locations

root_router = APIRouter()
root_router.include_router(animals.router)
root_router.include_router(users.router)
root_router.include_router(locations.router)
