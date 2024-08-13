import json
from datetime import datetime, timedelta
from decimal import Decimal

from app.models import Bet, BetStatus
from app.operations.event import get_event
from app.schemas import BetResponse, Event, EventState, PaginatedBetsHistory
from app.utils import LoggerConfigurator
from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = LoggerConfigurator(name="bet-operations").configure()


async def create_bet(
    event_id: str,
    amount: Decimal,
    session: AsyncSession,
) -> str:
    """Create a new bet."""
    async with session.begin():
        new_bet = Bet(event_id=event_id, amount=amount)
        session.add(new_bet)
        await session.flush()
        await session.refresh(new_bet)

        if new_bet.id is None:
            raise ValueError("Bet id is None after commit")

        return str(new_bet.id)


async def get_bets(page: int, size: int, session: AsyncSession) -> PaginatedBetsHistory:
    """Get all bets."""
    async with session.begin():
        query = select(func.count()).select_from(Bet)
        result = await session.execute(query)
        total = result.scalar_one()

        query = select(Bet.id, Bet.status)
        result = await session.execute(query.offset((page - 1) * size).limit(size))
        bet_ids_and_statuses = [
            BetResponse(id=id, status=status) for id, status in result.all()
        ]
        return PaginatedBetsHistory(
            items=bet_ids_and_statuses, total=total, page=page, size=size
        )


async def update_event_status(
    event: Event,
    session: AsyncSession,
    redis_client: Redis,
) -> dict[str, str]:
    """Update the status of an event for all bets on that event."""
    # Update event in cache
    # Try to get the event from cache
    try:
        cached_event = await redis_client.get(f"event:{event.event_id}")
    except Exception as e:
        logger.error(f"Failed to get event from cache: {e}")
        cached_event = None

    cached_event_data = json.loads(cached_event) if cached_event else {}
    event_data = cached_event_data.copy()
    for p_name, p_value in event.model_dump(exclude_unset=True).items():
        event_data[p_name] = p_value

    try:
        await redis_client.set(
            f"event:{event.event_id}", Event(**event_data).model_dump_json()
        )
    except Exception as e:
        logger.error(f"Failed to cache event: {event}, error: {e}")

    # Update all bets on that event
    if not event.state:
        return {"message": f"Event {event.event_id} has no changes for status"}

    if event.state == EventState.NEW:
        return {"message": f"Event {event.event_id} has no bets to update"}

    new_status = (
        BetStatus.WON if event.state == EventState.FINISHED_WIN else BetStatus.LOST
    )

    async with session.begin():
        query = (
            update(Bet)
            .where((Bet.event_id == event.event_id) & (Bet.status != new_status))
            .values(status=new_status)
        )

        result = await session.execute(query)

        if result.rowcount == 0:
            logger.info(f"No bets found for event {event.event_id}")

        await session.commit()

    return {"message": f"Updated {result.rowcount} bets for event {event.event_id}"}


async def update_not_playyed_bets(session: AsyncSession, redis_client: Redis) -> None:
    """Periodically update the status of not played bets."""
    logger.debug("Updating not played bets")
    async with session.begin():
        # Get all non played bets older than 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        query = select(Bet).where(
            Bet.status == BetStatus.NOT_PLAYED, Bet.created_at < cutoff_time
        )
        result = await session.execute(query)
        not_playyed_bets = result.scalars().all()
        logger.info(f"Found {len(not_playyed_bets)} not played bets")

        for bet in not_playyed_bets:
            try:
                event_data = await get_event(bet.event_id, redis_client=redis_client)
                if event_data["state"] != EventState.NEW:
                    bet.status = (
                        BetStatus.WON
                        if event_data["state"] == EventState.FINISHED_WIN
                        else BetStatus.LOST
                    )
            except HTTPException:
                # If we can't fetch the event data, we'll skip this bet for now
                continue

        await session.commit()
