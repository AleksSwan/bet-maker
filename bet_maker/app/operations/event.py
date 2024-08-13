import json
import time
from typing import List

import httpx
from app.config import settings
from app.utils import LoggerConfigurator
from redis.asyncio import Redis

logger = LoggerConfigurator(name="event-operations").configure()


async def get_event(event_id: str, redis_client: Redis) -> dict:
    logger.debug(f"get_event is called with event_id: {event_id}")

    # Try to get the event from cache
    try:
        cached_event = await redis_client.get(f"event:{event_id}")
    except Exception as e:
        logger.error(f"Failed to get event from cache: {e}")
        cached_event = None
    if cached_event:
        return json.loads(cached_event)

    # If not in cache, get from Line Provider service
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.line_provider_url}/events/{event_id}")
        response.raise_for_status()
        event_data = response.json()

        # Cache the event
        try:
            await redis_client.set(f"event:{event_id}", json.dumps(event_data))
        except Exception as e:
            logger.error(f"Failed to cache event: {event_data}, error: {e}")

        return event_data


async def get_available_events(redis_client: Redis) -> int:
    async with httpx.AsyncClient() as client:
        logger.info("Fetching events from Line Provider service")
        logger.debug(f"URL: {settings.line_provider_url}/events")
        events: List[dict] = []
        try:
            response = await client.get(f"{settings.line_provider_url}/events")
            response.raise_for_status()
        except (httpx.ConnectError, httpx.HTTPStatusError):
            logger.error("Failed to fetch events from Line Provider service")
        else:
            events = response.json()

        for event in events:
            event_id = event.get("event_id")
            if not event_id:
                logger.info(f"Skipping event with no ID: {event}")
                continue

            # Cache the event
            try:
                await redis_client.set(f"event:{event_id}", json.dumps(event))
            except Exception as e:
                logger.error(f"Failed to cache event: {event}, error: {e}")

    return len(events)


async def get_upcoming_events(redis_client: Redis) -> list[dict]:
    current_time = int(time.time())
    upcoming_events = []

    async for key in redis_client.scan_iter("event:*"):
        event_data = await redis_client.get(key)
        if event_data:
            event = json.loads(event_data)
            logger.debug(f"event: {event}")
            if event["deadline"] > current_time:
                upcoming_events.append(event)

    return upcoming_events
