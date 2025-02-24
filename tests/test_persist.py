import collections
import datetime
from unittest.mock import patch, create_autospec

import pytest
from kafka import KafkaConsumer, TopicPartition

from dataproduct_apps.config import Settings
from dataproduct_apps.kafka import value_serializer, value_deserializer
from dataproduct_apps.model import App
from dataproduct_apps.persist import _persist_records

TEST_TABLE = "test-table"

VALUE1 = App(datetime.datetime.now(), "fake-gcp", "app1", "team1", "", "team1", "image")
VALUE2 = App(datetime.datetime.now(), "fake-gcp", "app2", "team1", "", "team1", "image")

Value = collections.namedtuple("Value", ("serialized", "actual"))
FakeRecord = collections.namedtuple("FakeRecord", ("key", "value"))


def _serialized(value):
    return value_deserializer(value_serializer(value))


class TestPersist:
    @pytest.fixture
    def settings(self):
        return Settings(
            kafka_brokers="localhost:9092",
        )

    @pytest.fixture
    def values(self):
        return [
            Value(_serialized(VALUE1), VALUE1),
            Value(_serialized(VALUE2), VALUE2),
        ]

    @pytest.fixture
    def consumer(self, values):
        with patch("dataproduct_apps.kafka._create_consumer") as factory_mock:
            mock_consumer = create_autospec(KafkaConsumer, instance=True, _name="KafkaConsumerMock")
            factory_mock.return_value = mock_consumer
            mock_consumer.poll.side_effect = [
                {
                    TopicPartition("topic", 0): [
                        FakeRecord("1", values[0].serialized),
                        FakeRecord("2", values[1].serialized)
                    ]
                },
                {}
            ]
            yield mock_consumer

    @pytest.fixture
    def bq_client(self):
        with patch("dataproduct_apps.persist.bigquery.Client", autospec=True) as mock:
            yield mock

    def test_persist(self, settings, bq_client, consumer, values):
        row_count, error_count = _persist_records(settings, bq_client, TEST_TABLE)
        assert row_count == 2
        assert error_count == 0
        bq_client.insert_rows_json.assert_called_with(TEST_TABLE, [v.serialized for v in values])
        consumer.commit.assert_called_once()

    def test_error_handling(self, settings, bq_client, consumer):
        bq_client.insert_rows_json.return_value = [
            {
                "index": 2,
                "errors": [
                    {"reason": "Reason1", "message": "First row 2 error"},
                    {"reason": "Reason2", "message": "Second row 2 error", "location": "somewhere"},
                ]
            },
            {
                "index": 6,
                "errors": [
                    {"reason": "Reason3", "message": "First row 6 error"},
                    {"reason": "Reason4", "message": "Second row 6 error", "location": "somewhere else"},
                ]
            },
        ]
        row_count, error_count = _persist_records(settings, bq_client, TEST_TABLE)
        assert row_count == 0
        assert error_count == 2
        consumer.commit.assert_not_called()
