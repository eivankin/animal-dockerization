from tortoise.contrib.fastapi import register_tortoise
from fastapi import FastAPI

from constants import DB_URL, DEBUG
from models import Account, Account_Pydantic, AccountIn_Pydantic

app = FastAPI(debug=DEBUG)


@app.get("/accounts/{account_id}", response_model=Account_Pydantic)
async def get_account(account_id: int):
    return await Account_Pydantic.from_queryset_single(Account.get(id=account_id))


@app.post("/registration", response_model=Account_Pydantic)
async def create_account(account: AccountIn_Pydantic):
    return await Account_Pydantic.from_tortoise_orm(Account.create(**account.dict()))


if __name__ == "__main__":
    register_tortoise(
        app=app,
        db_url=DB_URL,
        modules={"models": ["models"]},
        generate_schemas=True,
        add_exception_handlers=True,
    )
