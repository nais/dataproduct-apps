import collections
from unittest.mock import patch, create_autospec

import pytest
from kafka import KafkaConsumer, TopicPartition

from dataproduct_apps.persist import _persist_records

TEST_TABLE = "test-table"

FakeRecord = collections.namedtuple("FakeRecord", ("key", "value"))


class TestPersist:
    @pytest.fixture
    def consumer(self):
        with patch("dataproduct_apps.kafka._create_consumer") as factory_mock:
            mock_consumer = create_autospec(KafkaConsumer, instance=True, _name="KafkaConsumerMock")
            factory_mock.return_value = mock_consumer
            mock_consumer.poll.side_effect = [
                {TopicPartition("topic", 0): [FakeRecord("1", "value1"), FakeRecord("2", "value2")]},
                {}
            ]
            yield mock_consumer

    @pytest.fixture
    def bq_client(self):
        with patch("dataproduct_apps.persist.bigquery.Client", autospec=True) as mock:
            yield mock

    def test_persist(self, bq_client, consumer):
        row_count, error_count = _persist_records(bq_client, TEST_TABLE)
        assert row_count == 2
        assert error_count == 0
        bq_client.insert_rows_json.assert_called_with(TEST_TABLE, ["value1", "value2"])
        consumer.commit.assert_called_once()

    def test_error_handling(self, bq_client, consumer):
        bq_client.insert_rows_json.return_value = {"2": ["first error", "second error"]}
        row_count, error_count = _persist_records(bq_client, TEST_TABLE)
        assert row_count == 0
        assert error_count == 1
        consumer.commit.assert_not_called()
