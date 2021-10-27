import logging
import os

from kafka import KafkaProducer, KafkaConsumer

from dataproduct_apps.model import _value_serializer, _value_deserializer

TOPIC = "aura.dataproduct-apps"
LOG = logging.getLogger(__name__)


def _create_consumer():
    return KafkaConsumer(
        bootstrap_servers=os.getenv("KAFKA_BROKERS"),
        group_id="dataproduct-apps",
        value_deserializer=_value_deserializer,
        security_protocol="SSL",
        ssl_cafile=os.getenv("KAFKA_CA_PATH"),
        ssl_certfile=os.getenv("KAFKA_CERTIFICATE_PATH"),
        ssl_keyfile=os.getenv("KAFKA_PRIVATE_KEY_PATH"),
        auto_offset_reset="earliest"
    )


def _create_producer():
    return KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BROKERS"),
        value_serializer=_value_serializer,
        acks="all",
        retries=3,
        security_protocol="SSL",
        ssl_cafile=os.getenv("KAFKA_CA_PATH"),
        ssl_certfile=os.getenv("KAFKA_CERTIFICATE_PATH"),
        ssl_keyfile=os.getenv("KAFKA_PRIVATE_KEY_PATH"),
    )


def publish(apps):
    producer = _create_producer()
    for app in apps:
        producer.send(TOPIC, app)
    producer.flush()
    producer.close()
    LOG.info("kafka producer metrics", producer.metrics(raw=False))


def receive():
    consumer = _create_consumer()
    LOG.info("receiving kafka messages...")
    for msg in consumer:
        yield msg.value
