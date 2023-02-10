from base64 import b64encode

import pytest
from asgi_lifespan import LifespanManager
from httpx import AsyncClient
from main import app
from models import Account, AccountIn

TEST_ACCOUNT = AccountIn(
    **{
        "firstName": "Name",
        "lastName": "Surname",
        "email": "name@example.com",
        "password": "password",
    }
)


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def client():
    async with LifespanManager(app):
        async with AsyncClient(app=app, base_url="http://test") as c:
            yield c


@pytest.fixture(scope="module")
def auth_headers() -> dict[str, str]:
    auth_data = TEST_ACCOUNT.email + ":" + TEST_ACCOUNT.password
    return {
        "Authorization": f"Basic {b64encode(bytes(auth_data, 'utf8')).decode('utf8')}"
    }


@pytest.mark.anyio
async def test_create_user(client: AsyncClient):
    response = await client.post(
        "/registration",
        json=TEST_ACCOUNT.dict(),
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["firstName"] == TEST_ACCOUNT.first_name
    assert "id" in data
    user_id = data["id"]

    user_obj = await Account.get(id=user_id)
    assert user_obj.id == user_id


@pytest.mark.anyio
async def test_create_user_blank_field(client: AsyncClient):
    account = TEST_ACCOUNT.copy()
    account.first_name = " "
    response = await client.post(
        "/registration",
        json=account.dict(),
    )
    assert response.status_code == 400, response.text


@pytest.mark.anyio
async def test_get_user(client: AsyncClient, auth_headers: dict[str, str]):
    client.headers.update(auth_headers)
    existing_user = await Account.get(email=TEST_ACCOUNT.email)
    response = await client.get(
        f"/accounts/{existing_user.id}",
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["firstName"] == TEST_ACCOUNT.first_name


# @pytest.mark.anyio
# async def test_get_user_unauthorized(client: AsyncClient):
#     client.headers.clear()
#     existing_user = await Account.get(email=TEST_ACCOUNT.email)
#     response = await client.get(
#         f"/accounts/{existing_user.id}",
#     )
#     assert response.status_code == 401, response.text


@pytest.mark.anyio
async def test_get_user_negative_id(client: AsyncClient, auth_headers: dict[str, str]):
    client.headers.update(auth_headers)
    response = await client.get(
        f"/accounts/-1",
    )
    assert response.status_code == 400, response.text


@pytest.mark.anyio
async def test_create_user_not_unique_email(client: AsyncClient):
    account = TEST_ACCOUNT.copy()
    account.first_name = "test"
    account.last_name = "test"
    client.headers.clear()
    response = await client.post(
        "/registration",
        json=account.dict(),
    )
    assert response.status_code == 409, response.text
