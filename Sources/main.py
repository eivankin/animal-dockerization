import pydantic
import tortoise
from fastapi.exceptions import RequestValidationError
from passlib.context import CryptContext
from tortoise.contrib.fastapi import register_tortoise
from fastapi import FastAPI, Depends, status, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import PlainTextResponse

from constants import DB_URL, DEBUG
from models import Account, Account_Pydantic, AccountIn

app = FastAPI(debug=DEBUG)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBasic(auto_error=False)


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
    return None
    # raise HTTPException(
    #     status_code=status.HTTP_401_UNAUTHORIZED,
    # )


def validate_id(id_val: int) -> int:
    if id_val < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    return id_val


@app.get("/accounts/{id_val}", response_model=Account_Pydantic)
async def get_account(
    account_id: int = Depends(validate_id),
    # current_user: Account = Depends(get_current_user)
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


register_tortoise(
    app=app,
    db_url=DB_URL,
    modules={"models": ["models"]},
    generate_schemas=True,
)
