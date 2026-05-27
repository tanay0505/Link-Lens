import pytest


@pytest.mark.asyncio
async def test_analytics_summary(client, auth_headers):
    # Create a URL first
    create = await client.post(
        "/api/v1/urls/shorten",
        json={"original_url": "https://github.com"},
        headers=auth_headers
    )
    short_code = create.json()["short_code"]

    response = await client.get(
        f"/api/v1/analytics/{short_code}/summary",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_clicks" in data
    assert "desktop_clicks" in data
    assert "mobile_clicks" in data
    assert "unique_countries" in data


@pytest.mark.asyncio
async def test_analytics_timeline(client, auth_headers):
    create = await client.post(
        "/api/v1/urls/shorten",
        json={"original_url": "https://github.com"},
        headers=auth_headers
    )
    short_code = create.json()["short_code"]

    response = await client.get(
        f"/api/v1/analytics/{short_code}/timeline?days=7",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7
    assert "date" in data[0]
    assert "clicks" in data[0]


@pytest.mark.asyncio
async def test_analytics_wrong_user(client, auth_headers):
    # Create URL with first user
    create = await client.post(
        "/api/v1/urls/shorten",
        json={"original_url": "https://github.com"},
        headers=auth_headers
    )
    short_code = create.json()["short_code"]

    # Try to access with different user
    await client.post("/api/v1/auth/register", json={
        "email": "otheruser@test.com",
        "password": "password123"
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": "otheruser@test.com",
        "password": "password123"
    })
    other_token = login.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = await client.get(
        f"/api/v1/analytics/{short_code}/summary",
        headers=other_headers
    )
    assert response.status_code == 404