from typing import Annotated

from fastapi import Depends
from confluent_kafka import Producer
import os


def get_kafka_producer() -> Producer:
    producer = Producer({
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS')
    })
    try:
        yield producer
    finally:
        producer.flush()


KafkaProducerDependency = Annotated[Producer, Depends(get_kafka_producer)]