from typing import List

from app.dependencies import get_redis_client, get_session
from app.operations.bet import update_event_status
from app.operations.event import get_upcoming_events
from app.schemas import Event, EventState
from app.utils import LoggerConfigurator
from fastapi import APIRouter, Depends, HTTPException, Path, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

logger = LoggerConfigurator(name="router-events").configure()

router = APIRouter()


@router.get("/events", response_model=List[Event])
async def retrieve_events(
    redis_client: Redis = Depends(get_redis_client),
) -> list[dict]:
    """Retrieve available events."""
    try:
        events: list[dict] = await get_upcoming_events(redis_client=redis_client)
    except Exception as e:
        detail = "Failed to retrieve events"
        logger.error(f"{detail}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )
    return events


@router.put("/events/{event_id}")
async def update_event(
    event: Event,
    event_id: str = Path(...),
    session: AsyncSession = Depends(get_session),
    redis_client: Redis = Depends(get_redis_client),
) -> dict[str, str]:
    """Update the status of an event."""
    logger.debug("Processing event (status) update request")
    logger.debug(f"Event: {event}")

    # Nessesery checks
    event_states = [state for state in EventState]
    if event.state and event.state not in event_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid event status"
        )

    # Update
    try:
        response = await update_event_status(
            event=event, session=session, redis_client=redis_client
        )
    except Exception as e:
        detail = "Failed to update event status"
        logger.error(f"{detail}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )

    return {"message": response.get("message") or "Event status updated successfully"}
