import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Awaitable, Callable, Coroutine, Dict, cast
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from app.dependencies import get_redis_client, get_session
from app.main import app_bet_maker as app
from app.schemas import BetCreate
from fastapi import status
from httpx import ASGITransport, AsyncClient, HTTPStatusError, Request
from sqlalchemy.ext.asyncio import AsyncSession

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


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


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


@pytest.mark.asyncio
@patch("app.routes.bets.get_event", new_callable=AsyncMock)
@patch("app.routes.bets.create_bet", new_callable=AsyncMock)
async def test_place_bet_success(
    mock_create_bet, mock_get_event, mock_session, async_client
):
    # Mocking future deadline
    future_deadline = int((datetime.utcnow() + timedelta(days=1)).timestamp())
    print(f"Future deadline: {future_deadline}")

    # Mocking the return value of get_event
    mock_get_event.return_value = {
        "event_id": "1",
        "name": "Test Event",
        "deadline": future_deadline,
    }

    # Arrange
    bet_create = BetCreate(event_id="1", amount=Decimal("100.00"))
    expected_bet_id = str(uuid.uuid4())

    mock_create_bet.return_value = expected_bet_id

    print(f"Mock create_bet set up: {mock_create_bet}")
    print(f"Expected bet ID: {expected_bet_id}")

    # Mock the get_session dependency
    app.dependency_overrides[get_session] = lambda: mock_session

    try:
        # Act
        payload = bet_create.model_dump()
        print(f"Request payload: {payload}")
        response = await async_client.post("/bets", json=payload)

        # Debug info
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        print(f"Mock create_bet called: {mock_create_bet.called}")
        print(f"Mock create_bet call count: {mock_create_bet.call_count}")
        print(f"Mock create_bet call args: {mock_create_bet.call_args}")

        # Assert
        assert mock_get_event.called, "get_event was not called"
        assert mock_create_bet.called, "create_bet was not called"
        mock_create_bet.assert_called_once()

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["id"] == expected_bet_id

    except Exception as e:
        print(f"Exception in test: {e}")
        import traceback

        print(traceback.format_exc())
        raise

    finally:
        # Clean up
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.routes.bets.get_event", new_callable=AsyncMock)
@patch("app.operations.bet.create_bet", new_callable=AsyncMock)
async def test_place_bet_failure(
    mock_create_bet,
    mock_get_event,
    mock_redis_client,
    async_client,
):

    # Mocking future deadline
    future_deadline = int((datetime.utcnow() + timedelta(days=1)).timestamp())

    # Mocking the return value of get_event
    mock_get_event.side_effect = httpx.HTTPStatusError(
        message="Simulated HTTP error",
        request=httpx.Request("GET", "http://localhost/bets"),
        response=httpx.Response(status_code=status.HTTP_400_BAD_REQUEST),
    )

    return_value = {"deadline": future_deadline}
    mock_redis_client.get.return_value = json.dumps(return_value)

    mock_create_bet.side_effect = Exception("Test exception")

    # Arrange
    bet_create = BetCreate(event_id="test_event", amount=Decimal("100.00"))

    # Act
    response = await async_client.post("/bets", json=bet_create.model_dump())

    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Unable to fetch event data"}
    mock_get_event.assert_called_once_with(
        event_id=bet_create.event_id, redis_client=mock_redis_client
    )
