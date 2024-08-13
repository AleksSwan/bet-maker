from datetime import datetime

import httpx
from app.dependencies import get_redis_client, get_session
from app.operations.bet import create_bet, get_bets
from app.operations.event import get_event
from app.schemas import BetCreate, BetCreateResponse, PaginatedBetsHistory
from app.tasks import update_pending_bets_scheduler
from app.utils import LoggerConfigurator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

logger = LoggerConfigurator(name="router-bets").configure()

router = APIRouter()


@router.post(
    "/bets",
    response_model=BetCreateResponse,
)
async def place_bet(
    bet: BetCreate,
    session: AsyncSession = Depends(get_session),
    redis_client: Redis = Depends(get_redis_client),
) -> JSONResponse:
    """Place a new bet."""
    logger.debug(f"Entering place_bet function with bet: {bet}")
    logger.debug(f"Using get_event function: {get_event}")

    # Check event deadline
    try:
        event_data = await get_event(event_id=bet.event_id, redis_client=redis_client)
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to fetch event data: {e}")
        if e.response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch event data",
        )

    try:
        deadline = datetime.fromtimestamp(event_data["deadline"])
    except (AttributeError, ValueError, TypeError) as e:
        logger.error(f"Invalid deadline format in event data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid deadline format in event data",
        )

    if deadline <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Betting deadline has passed",
        )

    try:
        bet_id = await create_bet(
            event_id=bet.event_id, amount=bet.amount, session=session
        )
    except Exception as e:
        detail = "Failed to create bet"
        logger.error(f"{detail}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )

    return JSONResponse(content={"id": str(bet_id)}, status_code=201)


@router.get(
    "/bets",
    response_model=PaginatedBetsHistory,
)
async def read_bets(
    page: int = 1,
    size: int = 50,
    session: AsyncSession = Depends(get_session),
) -> PaginatedBetsHistory:
    """Get all bets."""

    try:
        bets: PaginatedBetsHistory = await get_bets(
            page=page, size=size, session=session
        )
    except Exception as e:
        detail = "Failed to get bets"
        logger.error(f"{detail}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )

    return bets


@router.get(
    "/bets/check",
)
async def check_pended_bets() -> None:
    """Check if any bets are pending."""

    await update_pending_bets_scheduler()
