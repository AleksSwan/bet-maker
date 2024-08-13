import json
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Coroutine, Dict, cast
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from app.dependencies import get_redis_client, get_session
from app.main import app_bet_maker as app
from fastapi import status
from httpx import ASGITransport, AsyncClient, HTTPStatusError, Request

ASGIApp = Callable[
    [
        Dict[str, Any],
        Callable[[], Awaitable[Dict[str, Any]]],
        Callable[[Dict[str, Any]], Coroutine[None, None, None]],
    ],
    Coroutine[None, None, None],
]


@pytest.fixture
def mock_redis_client(monkeypatch):
    mock_redis = AsyncMock()
    monkeypatch.setattr("app.dependencies.get_redis_client", mock_redis)
    return mock_redis


@pytest_asyncio.fixture
async def async_client(mock_redis_client):
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_redis_client] = lambda: mock_redis_client

    transport = ASGITransport(app=cast(ASGIApp, app))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code, expected_status_code",
    [
        (status.HTTP_404_NOT_FOUND, status.HTTP_404_NOT_FOUND),
        (status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_500_INTERNAL_SERVER_ERROR),
        (status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR),
    ],
)
@patch("app.routes.bets.get_event", new_callable=AsyncMock)
@patch("app.operations.bet.create_bet", new_callable=AsyncMock)
async def test_place_bet_route_exists(
    mock_create_bet,
    mock_get_event,
    status_code,
    expected_status_code,
    mock_redis_client,
    async_client,
):

    # Mocking future deadline
    future_deadline = int((datetime.utcnow() + timedelta(days=1)).timestamp())

    # Mocking the return value of get_event
    mock_get_event.return_value = {
        "event_id": "1",
        "name": "Test Event",
        "deadline": future_deadline,
    }
    return_value = {"deadline": future_deadline}
    mock_redis_client.get.return_value = json.dumps(return_value)

    mock_request = AsyncMock(spec=Request)
    mock_get_event.side_effect = HTTPStatusError(
        "Error occurred",
        request=mock_request,
        response=AsyncMock(status_code=status_code),
    )

    # Perform the action
    response = await async_client.post("/bets", json={"event_id": "1", "amount": 100})

    # Assertions
    assert mock_get_event.called
    assert response.status_code == expected_status_code
