import enum
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Optional

import httpx
from aiokafka import AIOKafkaProducer  # type: ignore
from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel

BET_MAKER_URL = os.getenv("BET_MAKER_URL")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = "line_provider"

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

producer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.debug("Starting Line Provider service...")
    global producer

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()

    yield

    # Shutdown
    logger.debug("Stopping Line Provider service...")
    await producer.stop()


class EventState(enum.Enum):
    NEW = 1
    FINISHED_WIN = 2
    FINISHED_LOSE = 3


class Event(BaseModel):
    event_id: str
    coefficient: Optional[Decimal] = None
    deadline: Optional[int] = None
    state: Optional[EventState] = None


events: dict[str, Event] = {
    "1": Event(
        event_id="1",
        coefficient=Decimal("1.2"),
        deadline=int(time.time()) + 600,
        state=EventState.NEW,
    ),
    "2": Event(
        event_id="2",
        coefficient=Decimal("1.15"),
        deadline=int(time.time()) + 60,
        state=EventState.NEW,
    ),
    "3": Event(
        event_id="3",
        coefficient=Decimal("1.2"),
        deadline=int(time.time()) + 90,
        state=EventState.NEW,
    ),
}

app_line_provider = FastAPI(lifespan=lifespan)


@app_line_provider.put("/event")
async def create_event(event: Event):
    if event.event_id not in events:
        events[event.event_id] = event
    else:
        for p_name, p_value in event.model_dump(exclude_unset=True).items():
            setattr(events[event.event_id], p_name, p_value)

    try:
        await send_event(event=event)
    except Exception as e:
        logger.error(f"Failed to send event to Bet Maker service: {e}")

    return {}


async def send_event(event: Event):
    # Place for abstract logic
    await send_event_to_kafka(event=event)


async def send_event_to_kafka(event: Event):
    """Send event to Kafka"""
    if producer:
        message = event.model_dump_json(exclude_unset=True)
        await producer.send_and_wait(topic=KAFKA_TOPIC, value=message)
        logger.debug(f"Sent event to Kafka: {message}")
    else:
        logger.error("Kafka producer not initialized")


async def send_event_to_api(event: Event):
    """Send event to Bet Maker service"""
    async with httpx.AsyncClient() as client:
        logger.debug("Fetching events from Line Provider service")
        logger.debug(f"URL: {BET_MAKER_URL}/events/{event.event_id}")
        logger.debug(f"Body: {event.model_dump_json(exclude_unset=True)}")
        response = await client.put(
            f"{BET_MAKER_URL}/events/{event.event_id}",
            json=event.model_dump_json(exclude_unset=True),
        )
        response.raise_for_status()


@app_line_provider.get("/event/{event_id}")
async def get_event(event_id: str = Path(...)):
    if event_id in events:
        return events[event_id]

    raise HTTPException(status_code=404, detail="Event not found")


@app_line_provider.get("/events")
async def get_events():
    events_list = [
        e for e in events.values() if e.deadline and time.time() < e.deadline
    ]
    logger.debug(f"Found events: {events_list}")
    return events_list
