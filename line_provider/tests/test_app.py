import time
from typing import Any, Awaitable, Callable, Coroutine, Dict, cast

import pytest
from app.main import app_line_provider
from httpx import ASGITransport, AsyncClient

ASGIApp = Callable[
    [
        Dict[str, Any],
        Callable[[], Awaitable[Dict[str, Any]]],
        Callable[[Dict[str, Any]], Coroutine[None, None, None]],
    ],
    Coroutine[None, None, None],
]


@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_simple_workflow(anyio_backend):
    test_id = "test_id"

    test_event = {
        "event_id": test_id,
        "coefficient": "1.0",
        "deadline": int(time.time()) + 600,
        "state": 1,
    }
    transport = ASGITransport(app=cast(ASGIApp, app_line_provider))

    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        create_response = await ac.put("/event", json=test_event)

    assert create_response.status_code == 200

    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        response = await ac.get(f"/event/{test_id}")

    assert response.status_code == 200
    assert response.json() == test_event

    updated_event = test_event.copy()
    updated_event["state"] = 2

    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        update_response = await ac.put("/event", json={"event_id": test_id, "state": 2})

    assert update_response.status_code == 200

    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        response = await ac.get(f"/event/{test_id}")

    assert response.status_code == 200
    assert response.json() == updated_event
