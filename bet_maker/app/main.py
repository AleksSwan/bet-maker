import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from aiokafka import AIOKafkaConsumer  # type: ignore
from app.database import db
from app.dependencies import get_consumer
from app.errors import ConsumerStartError
from app.routes import bets, events
from app.tasks import (
    get_available_events_on_startup,
    process_message,
    update_pending_bets_scheduler,
)
from app.utils import LoggerConfigurator
from fastapi import FastAPI

logger: logging.Logger = LoggerConfigurator(name="app").configure()
consumer: Optional[AIOKafkaConsumer] = None
consume_task: Optional[asyncio.Task[None]] = None


async def consume_messages():
    global consumer
    while True and consumer:
        try:
            async for msg in consumer:
                try:
                    logger.info(f"Received message: {msg.value}")
                    await process_message(message=msg.value)
                    await consumer.commit()
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        except asyncio.CancelledError:
            logger.info("Consumer task was cancelled")
            break
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            await asyncio.sleep(5)
            # Attempt to reconnect
            try:
                await consumer.stop()
                await consumer.start()
            except Exception as reconnect_error:
                logger.error(f"Fialed to reconnect: {reconnect_error}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer, consume_task
    logger.info("Starting up")

    logger.info("Connecting to database")
    await db.connect()

    logger.info("Database connected")

    # Start periodic bets check task
    await update_pending_bets_scheduler()

    # Start available events getter task
    # TODO: Not situable for multiple instances, need better solution
    # May be better to use control events counter for interval
    await get_available_events_on_startup()

    # Set up consumer
    consumer = await get_consumer()

    # Start consumer
    try:
        await consumer.start()
    except Exception as e:
        logger.error(f"Failed to start consumer: {e}")
        raise ConsumerStartError("Failed to start consumer")

    # Start consumer task
    consume_task = asyncio.create_task(consume_messages())

    logger.info("Started up")

    yield

    logger.info("Shutting down")
    await db.disconnect()

    if consume_task:
        consume_task.cancel()
        await asyncio.wait([consume_task])
    await consumer.stop()

    logger.info("Shutdown complete")


app_bet_maker = FastAPI(lifespan=lifespan)

app_bet_maker.include_router(bets.router, prefix="")
app_bet_maker.include_router(events.router, prefix="")


@app_bet_maker.get("/health")
async def health_check() -> dict[str, str | bool]:
    """Health check"""
    return {
        "status": "OK",
        "consuumer_running": consume_task is not None and not consume_task.done(),
    }
