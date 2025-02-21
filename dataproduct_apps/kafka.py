import logging

from kafka import KafkaProducer, KafkaConsumer

from dataproduct_apps.config import Settings
from dataproduct_apps.model import value_serializer, value_deserializer

MINUTES_IN_MS = 60000
LOG = logging.getLogger(__name__)


def _create_consumer(settings: Settings):
    return KafkaConsumer(
        bootstrap_servers=settings.kafka_brokers,
        group_id=settings.nais_client_id,
        value_deserializer=value_deserializer,
        security_protocol=settings.kafka_security_protocol,
        ssl_cafile=settings.kafka_ca_path,
        ssl_certfile=settings.kafka_certificate_path,
        ssl_keyfile=settings.kafka_private_key_path,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )


def _create_producer(settings: Settings):
    return KafkaProducer(
        bootstrap_servers=settings.kafka_brokers,
        value_serializer=value_serializer,
        acks="all",
        retries=3,
        security_protocol=settings.kafka_security_protocol,
        ssl_cafile=settings.kafka_ca_path,
        ssl_certfile=settings.kafka_certificate_path,
        ssl_keyfile=settings.kafka_private_key_path,
    )


def publish(settings: Settings, items, topic):
    producer = _create_producer(settings)
    count = 0
    for item in items:
        try:
            key, value = item
            producer.send(topic, key=key, value=value)
        except TypeError:
            try:
                producer.send(topic, key=item.key(), value=item)
            except AttributeError:
                producer.send(topic, value=item)
        count += 1
    LOG.info("Sent %d messages to Kafka", count)
    producer.flush()
    LOG.info("kafka producer metrics %s", producer.metrics(raw=False))
    producer.close()


def receive(settings: Settings, topic):
    """Yields a dictionary {TopicPartition: [messages]}"""
    consumer = _create_consumer(settings)
    LOG.info("receiving kafka messages...")
    consumer.subscribe([topic])
    while True:
        records = consumer.poll(1 * MINUTES_IN_MS)
        if records:
            yield records
            consumer.commit()
        else:
            break
