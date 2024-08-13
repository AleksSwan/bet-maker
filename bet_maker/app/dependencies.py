import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Tuple

from aiokafka import AIOKafkaConsumer  # type: ignore
from app.config import settings
from app.database import AsyncSessionLocal
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis_client() -> Redis:
    if not settings.redis_url:
        raise ValueError("Redis URL not set")

    redis_client = Redis.from_url(
        settings.redis_url, encoding="utf-8", decode_responses=True
    )
    return redis_client


async def get_consumer() -> AIOKafkaConsumer:
    if not all(
        [
            settings.kafka_events_update_topic,
            settings.kafka_bootstrap_servers,
            settings.kafka_consumer_group,
        ]
    ):
        raise ValueError("Kafka settings not set")

    consumer = AIOKafkaConsumer(
        settings.kafka_events_update_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    return consumer


@asynccontextmanager
async def get_db_and_redis() -> AsyncGenerator[Tuple[AsyncSession, Redis], None]:
    session_gen = get_session()
    try:
        session = await session_gen.__anext__()
        redis_client = await get_redis_client()
        try:
            yield session, redis_client
        finally:
            await redis_client.close()
    finally:
        try:
            await session_gen.__anext__()
        except StopAsyncIteration:
            pass
