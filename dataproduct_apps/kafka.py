import dataclasses
import datetime
import json
import logging

from kafka import KafkaProducer, KafkaConsumer

from dataproduct_apps.config import Settings

MINUTES_IN_MS = 60000
LOG = logging.getLogger(__name__)

_SENTINEL = object()


def _create_consumer(settings: Settings, group_id=_SENTINEL):
    if group_id is _SENTINEL:
        group_id = settings.nais_client_id
    return KafkaConsumer(
        bootstrap_servers=settings.kafka_brokers,
        group_id=group_id,
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


def receive_from_compacted(settings: Settings, topic):
    """Yields a dictionary {TopicPartition: [messages]}"""
    consumer = _create_consumer(settings, group_id=None)
    LOG.info("receiving kafka messages...")
    consumer.subscribe([topic])
    while True:
        records = consumer.poll(1 * MINUTES_IN_MS)
        if records:
            yield records
        else:
            break


def value_serializer(value):
    try:
        data = dataclasses.asdict(value)
    except TypeError:
        try:
            data = value.as_dict()
        except AttributeError:
            data = value
    if data and "collection_time" in data:
        data["collection_time"] = datetime.datetime.isoformat(data["collection_time"])
    return json.dumps(data).encode("utf-8")


def value_deserializer(bytes):
    return json.loads(bytes.decode("utf-8"))
