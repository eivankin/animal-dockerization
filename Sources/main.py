import pydantic
import tortoise
from fastapi.exceptions import RequestValidationError
from tortoise.contrib.fastapi import register_tortoise
from fastapi import FastAPI, status
from fastapi.responses import PlainTextResponse

from config import DB_URL, DEBUG
from models import orm
from routers import root_router

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
