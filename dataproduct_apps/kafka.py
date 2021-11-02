import logging
import os

from kafka import KafkaProducer, KafkaConsumer

from dataproduct_apps.model import value_serializer, value_deserializer

TOPIC = "aura.dataproduct-apps"
MINUTES_IN_MS = 60000
LOG = logging.getLogger(__name__)


def _create_consumer():
    return KafkaConsumer(
        bootstrap_servers=os.getenv("KAFKA_BROKERS"),
        group_id="dataproduct-apps",
        value_deserializer=value_deserializer,
        security_protocol="SSL",
        ssl_cafile=os.getenv("KAFKA_CA_PATH"),
        ssl_certfile=os.getenv("KAFKA_CERTIFICATE_PATH"),
        ssl_keyfile=os.getenv("KAFKA_PRIVATE_KEY_PATH"),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )


def _create_producer():
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
    producer = _create_producer()
    count = 0
    for app in apps:
        producer.send(TOPIC, app)
        count += 1
    LOG.info("Sent %d messages to Kafka", count)
    producer.flush()
    LOG.info("kafka producer metrics %s", producer.metrics(raw=False))
    producer.close()


def receive():
    """Yields a dictionary {TopicPartition: [messages]}"""
    consumer = _create_consumer()
    LOG.info("receiving kafka messages...")
    consumer.subscribe([TOPIC])
    while True:
        records = consumer.poll(1 * MINUTES_IN_MS)
        if records:
            yield records
            consumer.commit()
        else:
            break
