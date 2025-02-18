import dataclasses
import json
import unittest
from base64 import b64decode
from datetime import datetime

import pytest
import requests
import requests_toolbelt.utils.dump
from k8s.models.common import ObjectMeta

from dataproduct_apps import kafka
from dataproduct_apps.crd import Topic, TopicSpec, TopicAccess
from dataproduct_apps.model import TopicAccessApp, AppRef

POOL = "dev-nais-local"

CLUSTER_TOPICS = [
    Topic(
        metadata=ObjectMeta(name="topic1", namespace="namespace1"),
        spec=TopicSpec(
            pool=POOL,
            acl=[
                TopicAccess(access="read", application="app1", team="namespace1"),
            ]),
    ),
    Topic(
        metadata=ObjectMeta(name="topic2", namespace="namespace2"),
        spec=TopicSpec(
            pool=POOL,
            acl=[
                TopicAccess(access="read", application="app1", team="namespace1"),
                TopicAccess(access="write", application="app2", team="namespace2"),
            ]),
    ),
    Topic(
        metadata=ObjectMeta(name="topic3", namespace="namespace3"),
        spec=TopicSpec(
            pool=POOL,
            acl=[
                TopicAccess(access="readwrite", application="app1", team="namespace1"),
            ]),
    ),
]

EXPECTED_TOPIC_ACCESSES = [
    TopicAccessApp(pool=POOL, team="namespace1", namespace="namespace1", topic="topic1", access="read", app=AppRef(namespace="namespace1", name="app1")),
    TopicAccessApp(pool=POOL, team="namespace2", namespace="namespace2", topic="topic2", access="read", app=AppRef(namespace="namespace1", name="app1")),
    TopicAccessApp(pool=POOL, team="namespace2", namespace="namespace2", topic="topic2", access="write", app=AppRef(namespace="namespace2", name="app2")),
    TopicAccessApp(pool=POOL, team="namespace3", namespace="namespace3", topic="topic3", access="readwrite", app=AppRef(namespace="namespace1", name="app1")),
]

TEST_HOST = "localhost"
STORAGE_PORT = 9023
KAFKA_PORT = 9092
KAFKA_REST_PORT = 8082
BUCKET = "dataproduct-apps-topics2"


@pytest.mark.integration
class TestINTEGRATION:
    @pytest.fixture(autouse=True)
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("STORAGE_EMULATOR_HOST", f"http://{TEST_HOST}:{STORAGE_PORT}")
        monkeypatch.setenv("NAIS_CLUSTER_NAME", POOL)
        monkeypatch.setenv("KAFKA_BROKERS", f"{TEST_HOST}:{KAFKA_PORT}")
        monkeypatch.setenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")

    @pytest.fixture
    def storage_client(self, mock_env):
        from google.cloud import storage
        return storage.Client()

    @pytest.fixture()
    def bucket(self, storage_client):
        from google.cloud import exceptions
        try:
            return storage_client.create_bucket("dataproduct-apps-topics2")
        except exceptions.Conflict:
            return storage_client.bucket("dataproduct-apps-topics2")

    def test_integration_topics(self, request, bucket):
        from dataproduct_apps.main import topics
        with unittest.mock.patch("dataproduct_apps.topics.Topic.list") as mock:
            mock.return_value = CLUSTER_TOPICS
            topics()
            _assert_bucket_contents(bucket)
            _assert_topic_contents(request)


def _assert_bucket_contents(bucket):
    blob = bucket.blob("topics_dev-nais-local.json")
    assert blob.exists()
    content = json.loads(blob.download_as_bytes())
    assert len(content) == len(CLUSTER_TOPICS)


def _assert_topic_contents(request):
    resp = requests.get(f"http://{TEST_HOST}:{KAFKA_REST_PORT}/topics")
    resp.raise_for_status()
    topics = resp.json()
    assert len(topics) == 1
    assert topics[0] == kafka.TOPIC_TOPIC
    resp = requests.post(f"http://{TEST_HOST}:{KAFKA_REST_PORT}/consumers/test-consumer-{request.node.originalname}-{datetime.now().isoformat()}", json={"auto.offset.reset": "earliest"}, headers={"Content-Type": "application/vnd.kafka.v2+json"})
    print(requests_toolbelt.utils.dump.dump_all(resp).decode("utf-8"))
    resp.raise_for_status()
    consumer_uri = resp.json()["base_uri"]
    print(f"Consumer URI: {consumer_uri}")
    resp = requests.post(f"{consumer_uri}/subscription", json={"topics": [kafka.TOPIC_TOPIC]}, headers={"Content-Type": "application/vnd.kafka.v2+json"})
    print(requests_toolbelt.utils.dump.dump_all(resp).decode("utf-8"))
    resp.raise_for_status()
    resp = requests.get(f"{consumer_uri}/records")
    print(requests_toolbelt.utils.dump.dump_all(resp).decode("utf-8"))
    resp.raise_for_status()
    records = resp.json()
    assert len(records) == 4
    assert [json.loads(b64decode(r["value"])) for r in records] == [dataclasses.asdict(t) for t in EXPECTED_TOPIC_ACCESSES]
