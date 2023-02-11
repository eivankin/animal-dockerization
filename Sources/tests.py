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
BAD_HEADER = (
    "Basic ZWQ4YzgwZDAtMjZlZi00NjEzLWFiOGYtNGVkNDkxZjAyOTNkOjMxZjc3NThkL"
    "WZhMTYtNDJmNy1iNjMzLWNjYmYxYzIzNmQ3Nw=="
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
async def test_create_user_invalid_email(client: AsyncClient):
    account = TEST_ACCOUNT.copy()
    account.email = "sus"
    response = await client.post(
        "/registration",
        json=account.dict(),
    )
    assert response.status_code == 400, response.text


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


@pytest.mark.anyio
async def test_get_user_unauthorized(client: AsyncClient, auth_headers: dict[str, str]):
    client.headers.clear()
    headers = auth_headers.copy()
    headers["Authorization"] = BAD_HEADER
    client.headers.update(headers)
    existing_user = await Account.get(email=TEST_ACCOUNT.email)
    response = await client.get(
        f"/accounts/{existing_user.id}",
    )
    assert response.status_code == 401, response.text


@pytest.mark.anyio
async def test_get_user_negative_id(client: AsyncClient, auth_headers: dict[str, str]):
    client.headers.update(auth_headers)
    response = await client.get(
        f"/accounts/-1",
    )
    assert response.status_code == 400, response.text


@pytest.mark.anyio
async def test_create_user_not_unique_email(client: AsyncClient):
    client.headers.clear()
    account = TEST_ACCOUNT.copy()
    account.first_name = "test"
    account.last_name = "test"
    client.headers.clear()
    response = await client.post(
        "/registration",
        json=account.dict(),
    )
    assert response.status_code == 409, response.text


@pytest.mark.anyio
async def test_search_user(client: AsyncClient):
    response = await client.get(
        f"/accounts/search?email={TEST_ACCOUNT.email[:5].upper()}"
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 1
    assert data[0]["firstName"] == TEST_ACCOUNT.first_name


@pytest.mark.anyio
async def test_search_user_invalid(client: AsyncClient):
    response = await client.get(
        f"/accounts/search?from=-1&email={TEST_ACCOUNT.email[:5].upper()}"
    )
    assert response.status_code == 400, response.text


@pytest.mark.anyio
async def test_delete_nonexistent_location(
    client: AsyncClient, auth_headers: dict[str, str]
):
    client.headers.update(auth_headers)
    response = await client.delete(
        f"/locations/1",
    )
    assert response.status_code == 404, response.text


@pytest.mark.anyio
async def test_create_animal(client: AsyncClient, auth_headers: dict[str, str]):
    client.headers.update(auth_headers)
    await client.post(
        "/locations",
        json={
            "latitude": 37.7882,
            "longitude": -122.4324,
        },
    )

    await client.post("/animals/types", json={"type": "cat"})

    response = await client.post(
        "/animals",
        json={
            "animalTypes": [1],
            "weight": 2315.8057,
            "length": 12.2942915,
            "height": 2.0351095,
            "gender": "FEMALE",
            "chipperId": 1,
            "chippingLocationId": 1,
        },
    )
    assert response.status_code == 201, response.text


@pytest.mark.anyio
async def test_get_animal(client: AsyncClient):
    response = await client.get("/animals/1")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "animalTypes" in data


@pytest.mark.anyio
async def test_add_animal_location(client: AsyncClient, auth_headers: dict[str, str]):
    client.headers.update(auth_headers)
    response = await client.post(
        "/locations",
        json={
            "latitude": 0,
            "longitude": 0,
        },
    )
    loc_id = response.json()["id"]

    response = await client.post(
        f"/animals/1/locations/{loc_id}",
    )
    assert response.status_code == 201, response.text


@pytest.mark.anyio
async def test_get_animal_locations(client: AsyncClient):
    response = await client.get("/animals/1/locations")
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) > 0


@pytest.mark.anyio
async def test_get_animals(client: AsyncClient):
    response = await client.get("/animals/search")
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) > 0


@pytest.mark.anyio
async def test_update_animal(client: AsyncClient, auth_headers: dict[str, str]):
    client.headers.update(auth_headers)

    response = await client.put(
        "/animals/1",
        json={
            "animalTypes": [1],
            "weight": 2315.8057,
            "length": 12.2942915,
            "height": 2.0351095,
            "gender": "MALE",
            "chipperId": 1,
            "chippingLocationId": 1,
            "lifeStatus": "DEAD",
        },
    )
    assert response.status_code == 200, response.text


# @pytest.mark.anyio
# async def test_delete_animal(client: AsyncClient, auth_headers: dict[str, str]):
#     client.headers.update(auth_headers)
#
#     response = await client.delete(
#         "/animals/1",
#     )
#     assert response.status_code == 200, response.text
