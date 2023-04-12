from fastapi import APIRouter
from routers.users import accounts, registration

router = APIRouter()
router.include_router(accounts.router)
router.include_router(registration.router)
