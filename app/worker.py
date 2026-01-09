import os, json
import aio_pika
from aio_pika import ExchangeType

RABBIT_URL = os.getenv("RABBIT_URL")
EXCHANGE_NAME = "accounts_topic"

async def publish_accounts_created(event: dict) -> None:
    conn = await aio_pika.connect_robust(RABBIT_URL)
    ch = await conn.channel()
    ex = await ch.declare_exchange(EXCHANGE_NAME, ExchangeType.TOPIC, durable=True)

    msg = aio_pika.Message(body=json.dumps(event).encode())
    await ex.publish(msg, routing_key="accounts.created")

    await conn.close()


async def publish_accounts_deleted(event: dict) -> None:
    conn = await aio_pika.connect_robust(RABBIT_URL)
    ch = await conn.channel()
    ex = await ch.declare_exchange(EXCHANGE_NAME, ExchangeType.TOPIC, durable=True)

    msg = aio_pika.Message(body=json.dumps(event).encode())
    await ex.publish(msg, routing_key="accounts.deleted")

    await conn.close()
