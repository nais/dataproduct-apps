import dataclasses
import datetime
import json
import os

from kafka import KafkaProducer

TOPIC = "aura.dataproduct-apps"


def value_serializer(app):
    data = dataclasses.asdict(app)
    data["collection_time"] = datetime.datetime.isoformat(data["collection_time"])
    return json.dumps(data).encode("utf-8")


def create_producer():
    return KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BROKERS"),
        value_serializer=value_serializer,
        acks="all",
        retries=3,
        security_protocol="SSL",
        ssl_cafile=os.getenv("KAFKA_CA_PATH"),
        ssl_certfile=os.getenv("KAFKA_CERTIFICATE_PATH"),
        ssl_keyfile=os.getenv("KAFKA_PRIVATE_KEY_PATH"),
    )


def publish(apps):
    producer = create_producer()
    for app in apps:
        producer.send(TOPIC, app)
    producer.flush()
    producer.close()
