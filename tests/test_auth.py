import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@test.com",
        "password": "password123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    # Register once
    await client.post("/api/v1/auth/register", json={
        "email": "duplicate@test.com",
        "password": "password123"
    })
    # Register again with same email
    response = await client.post("/api/v1/auth/register", json={
        "email": "duplicate@test.com",
        "password": "password123"
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "notanemail",
        "password": "password123"
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={
        "email": "loginuser@test.com",
        "password": "password123"
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "loginuser@test.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "email": "wrongpass@test.com",
        "password": "correctpass"
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "wrongpass@test.com",
        "password": "wrongpass"
    })
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    response = await client.post("/api/v1/auth/login", json={
        "email": "nobody@test.com",
        "password": "password123"
    })
    assert response.status_code == 401