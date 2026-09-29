"""Kafka transport wrapper.

Kafka is only a transport here. The same ServiceHandler used by HTTP handles the
request. The wrapper consumes `input_topic` and publishes the response to
`output_topic` for this phase.
"""
import asyncio

from .contracts import ServiceRequest, encode_json, decode_json
from .runner import ServiceHandler


class KafkaWrapper:
    def __init__(self, phase, *, bootstrap_servers: str, input_topic: str, output_topic: str,
                 group_id: str, client_id: str | None = None):
        self.handler = ServiceHandler(phase)
        self.bootstrap_servers = bootstrap_servers
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.group_id = group_id
        self.client_id = client_id or f"{phase.name}-ml"

    async def run(self) -> None:
        try:
            from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("Kafka serving requires the 'kafka' optional dependency") from exc

        consumer = AIOKafkaConsumer(
            self.input_topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            client_id=self.client_id,
        )
        producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id,
        )
        await consumer.start()
        await producer.start()
        try:
            async for message in consumer:
                request = ServiceRequest.from_dict(decode_json(message.value))
                response = self.handler.handle(request)
                await producer.send_and_wait(self.output_topic, encode_json(response.to_dict()))
        finally:
            await consumer.stop()
            await producer.stop()

    def start(self) -> None:
        asyncio.run(self.run())
