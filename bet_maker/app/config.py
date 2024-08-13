import os

from dotenv import load_dotenv

load_dotenv(override=True)


class Settings:
    redis_url = os.getenv("REDIS_URL")
    line_provider_url = os.getenv("LINE_PROVIDER_URL")
    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    kafka_events_update_topic = "line_provider"
    kafka_consumer_group = "bet_maker"
    database_url = (
        f"postgresql+asyncpg://{os.getenv('BET_MAKER_DB_USER')}:{os.getenv('BET_MAKER_DB_PASSWORD')}"
        f"@{os.getenv('BET_MAKER_DB_HOST')}:{os.getenv('BET_MAKER_DB_PORT')}/{os.getenv('BET_MAKER_POSTGRES_DB')}"
    )


settings = Settings()
