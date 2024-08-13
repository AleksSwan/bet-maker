import logging

from app.dependencies import get_db_and_redis
from app.operations.bet import update_event_status, update_not_playyed_bets
from app.operations.event import get_available_events
from app.schemas import Event
from app.utils import LoggerConfigurator
from fastapi_utils.tasks import repeat_every  # type: ignore

logger: logging.Logger = LoggerConfigurator(name="tasks").configure()


@repeat_every(seconds=60 * 60)  # Run every hour
async def update_pending_bets_scheduler() -> None:
    """Check for unplayed bets"""
    logger.info("Starting update pending bets task")

    try:
        async with get_db_and_redis() as (session, redis_client):
            await update_not_playyed_bets(session=session, redis_client=redis_client)
    except Exception as e:
        logger.error(f"Error during update_pending_bets_scheduler: {e}")

    logger.info("Update pending bets task complete")


async def get_available_events_on_startup() -> None:
    """Fetch available events on startup"""
    logger.info("Start up get available events task")

    try:
        async with get_db_and_redis() as (_, redis_client):
            count = await get_available_events(redis_client=redis_client)
    except Exception as e:
        logger.error(f"Error during get_available_events_on_startup: {e}")
    else:
        logger.info(f"Found {count} available events")

    logger.info("Get available events task complete")


async def process_message(message: str) -> None:
    """Message processor"""
    logger.debug(f"Processing message: {message}")

    try:
        event: Event = Event.parse_raw(message)
        async with get_db_and_redis() as (session, redis_client):
            # Create or update event
            response = await update_event_status(
                event=event, session=session, redis_client=redis_client
            )
            logger.info(f"Response: {response}")
    except Exception as e:
        logger.error(f"Error during processing message: {e}")
