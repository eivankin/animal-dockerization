import pydantic
import tortoise
from fastapi.exceptions import RequestValidationError
from tortoise.contrib.fastapi import register_tortoise
from fastapi import FastAPI, status
from fastapi.responses import PlainTextResponse

from config import DB_URL, DEBUG
from models import orm
from routers import root_router
from routers.users.utils import get_password_hash

app = FastAPI(debug=DEBUG)
app.include_router(root_router)


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


register_tortoise(
    app=app,
    db_url=DB_URL,
    modules={"models": [orm]},
    generate_schemas=True,
)


@app.on_event("startup")
async def create_accounts():
    default_pwd = get_password_hash("qwerty123")
    await orm.Account.get_or_create(
        first_name="adminFirstName",
        last_name="adminLastName",
        email="admin@simbirsoft.com",
        password_hash=default_pwd,
        role=orm.AccountRole.ADMIN,
    )
    await orm.Account.get_or_create(
        first_name="chipperFirstName",
        last_name="chipperLastName",
        email="chipper@simbirsoft.com",
        password_hash=default_pwd,
        role=orm.AccountRole.CHIPPER,
    )
    await orm.Account.get_or_create(
        first_name="userFirstName",
        last_name="userLastName",
        email="user@simbirsoft.com",
        password_hash=default_pwd,
        role=orm.AccountRole.USER,
    )
