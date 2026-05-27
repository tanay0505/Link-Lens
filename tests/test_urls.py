import pytest


@pytest.mark.asyncio
async def test_shorten_url_success(client, auth_headers):
    response = await client.post(
        "/api/v1/urls/shorten",
        json={"original_url": "https://github.com"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://github.com/"
    assert data["is_active"] is True
    assert data["click_count"] == 0


@pytest.mark.asyncio
async def test_shorten_url_with_custom_alias(client, auth_headers):
    response = await client.post(
        "/api/v1/urls/shorten",
        json={
            "original_url": "https://github.com",
            "custom_alias": "mygithub"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["short_code"] == "mygithub"


@pytest.mark.asyncio
async def test_shorten_url_duplicate_alias(client, auth_headers):
    await client.post(
        "/api/v1/urls/shorten",
        json={
            "original_url": "https://github.com",
            "custom_alias": "dupalias"
        },
        headers=auth_headers
    )
    response = await client.post(
        "/api/v1/urls/shorten",
        json={
            "original_url": "https://google.com",
            "custom_alias": "dupalias"
        },
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "already taken" in response.json()["detail"]


@pytest.mark.asyncio
async def test_shorten_url_invalid_url(client, auth_headers):
    response = await client.post(
        "/api/v1/urls/shorten",
        json={"original_url": "not-a-url"},
        headers=auth_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shorten_url_unauthenticated(client):
    response = await client.post(
        "/api/v1/urls/shorten",
        json={"original_url": "https://github.com"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_urls(client, auth_headers):
    response = await client.get("/api/v1/urls", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_redirect(client, auth_headers):
    # Create URL first
    create = await client.post(
        "/api/v1/urls/shorten",
        json={"original_url": "https://github.com"},
        headers=auth_headers
    )
    short_code = create.json()["short_code"]

    # Test redirect — don't follow it
    response = await client.get(
        f"/{short_code}",
        follow_redirects=False
    )
    assert response.status_code == 302
    assert "github.com" in response.headers["location"]


@pytest.mark.asyncio
async def test_redirect_invalid_code(client):
    response = await client.get("/invalidcode999", follow_redirects=False)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deactivate_url(client, auth_headers):
    create = await client.post(
        "/api/v1/urls/shorten",
        json={"original_url": "https://github.com"},
        headers=auth_headers
    )
    short_code = create.json()["short_code"]

    response = await client.delete(
        f"/api/v1/urls/{short_code}",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "deactivated" in response.json()["message"]
    