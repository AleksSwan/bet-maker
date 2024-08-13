import uuid
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models import BetStatus
from app.routes.bets import read_bets
from app.schemas import BetResponse, PaginatedBetsHistory
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Select


@pytest.fixture
def session_mock():
    session_mock = AsyncMock(spec=AsyncSession)

    # Mock the context manager
    session_mock.__aenter__.return_value = session_mock
    session_mock.__aexit__.return_value = None

    return session_mock


@pytest.mark.asyncio
async def test_read_bets_success(session_mock: AsyncSession):
    # Arrange
    expected_bets = [
        BetResponse(id=uuid.uuid4(), status=BetStatus.NOT_PLAYED),
        BetResponse(id=uuid.uuid4(), status=BetStatus.NOT_PLAYED),
    ]

    # Mock the execute result
    mock_result = MagicMock()
    mock_result.all.return_value = [(bet.id, bet.status) for bet in expected_bets]

    # Use patch to mock the execute method
    with patch.object(session_mock, "execute", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = mock_result

        # Act
        page = 1
        size = 10
        result = await read_bets(page=page, size=size, session=session_mock)

        # Assert
        # cast(AsyncMock, session_mock.execute).assert_called_once()
        execute_call_args = cast(AsyncMock, session_mock.execute).call_args
        assert isinstance(execute_call_args[0][0], Select)
        assert isinstance(result, PaginatedBetsHistory)
        assert result.items == expected_bets

    # Check if begin was called
    cast(AsyncMock, session_mock.begin).assert_called_once()


@pytest.mark.asyncio
async def test_read_bets_exception(session_mock: AsyncSession):
    # Arrange
    with patch.object(session_mock, "execute", side_effect=Exception("Some error")):

        # Act
        with pytest.raises(HTTPException) as exc_info:
            await read_bets(session=session_mock)

        # Assert
        assert str(exc_info.value.detail) == "Failed to get bets"
