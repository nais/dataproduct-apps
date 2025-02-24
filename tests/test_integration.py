import json
import time
import unittest
from base64 import b64decode, b64encode
from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest
import requests
import yaml
from k8s.base import Model
from k8s.fields import ListField
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError
from requests_toolbelt.utils.dump import dump_all

from dataproduct_apps.config import Settings
from dataproduct_apps.crd import Topic, Application, SqlInstance
from dataproduct_apps.kafka import value_serializer

POOL = "dev-nais-local"
TEST_HOST = "localhost"
STORAGE_PORT = 9023
KAFKA_PORT = 9092
KAFKA_REST_PORT = 8082
BUCKET = "dataproduct-apps-topics2"


class K8sClusterData(Model):
    topics = ListField(Topic)
    applications = ListField(Application)
    sql_instances = ListField(SqlInstance)


@dataclass
class TopicData:
    existing: list[Topic]
    expected_topics: list[Topic]
    expected_tombstones: list[str]


class KafkaRest:
    def __init__(self):
        self.base_uri = f"http://{TEST_HOST}:{KAFKA_REST_PORT}"
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/vnd.kafka.binary.v2+json",
        })

    def __getattr__(self, item):
        f = getattr(self._session, item)

        def wrapper(*args, **kwargs):
            uri = args[0]
            if not uri.startswith("http"):
                uri = f"{self.base_uri}/{uri}"
            return f(uri, *args[1:], **kwargs)

        return wrapper


@pytest.mark.integration
class TestIntegration:
    @pytest.fixture(scope="module")
    def settings(self, request):
        run_id = datetime.now().strftime("%Y%m%d%H%M%S")
        return Settings(
            nais_client_id=f"test-{request.session.name}-{run_id}",
            nais_cluster_name=POOL,
            kafka_brokers=f"{TEST_HOST}:{KAFKA_PORT}",
            kafka_security_protocol="PLAINTEXT",
            topic_topic=f"nais.dataproduct-apps-topics-{run_id}",
            app_topic=f"aura.dataproduct-apps-{run_id}",
        )

    @pytest.fixture(scope="module")
    def topic(self, request, settings):
        admin_client = KafkaAdminClient(
            bootstrap_servers=settings.kafka_brokers,
            client_id=settings.nais_client_id,
        )
        deadline = datetime.now() + timedelta(seconds=30)
        last_exception = None
        while datetime.now() < deadline:
            try:
                admin_client.create_topics([
                    NewTopic(
                        name=settings.topic_topic,
                        num_partitions=1,
                        replication_factor=1,
                        topic_configs={"cleanup.policy": "compact"},
                    ),
                    NewTopic(
                        name=settings.app_topic,
                        num_partitions=1,
                        replication_factor=1,
                        topic_configs={"cleanup.policy": "delete"},
                    ),
                ])
            except TopicAlreadyExistsError:
                return
            except Exception as e:
                last_exception = e
                time.sleep(1)
        raise last_exception

    @pytest.fixture(scope="module")
    def kafka_rest(self):
        return KafkaRest()

    @pytest.fixture(scope="module")
    def k8s_cluster_data(self, request) -> K8sClusterData:
        data_file = request.path.parent / "integration_test_data" / "k8s_cluster.yaml"
        with open(data_file) as f:
            data = yaml.safe_load(f)
            return K8sClusterData.from_dict(data)

    @pytest.fixture(scope="module")
    def topic_data(self, request, settings, kafka_rest) -> TopicData:
        data_file = request.path.parent / "integration_test_data" / "topic_topic.yaml"
        topic_data = TopicData([], [], [])
        with open(data_file) as f:
            data = yaml.safe_load(f)
            for d in data["existing"]:
                t = Topic.from_dict(d)
                value = value_serializer(d)
                resp = kafka_rest.post(f"topics/{settings.topic_topic}", json={
                    "records": [
                        {
                            "key": b64encode(t.key()).decode("utf-8"),
                            "value": b64encode(value).decode("utf-8"),
                        }
                    ]
                })
                resp.raise_for_status()
                topic_data.existing.append(t)
            topic_data.expected_topics = [Topic.from_dict(d) for d in data["expected_topics"]]
            topic_data.expected_tombstones = data["expected_tombstones"]
        return topic_data

    @pytest.fixture(autouse=True)
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("STORAGE_EMULATOR_HOST", f"http://{TEST_HOST}:{STORAGE_PORT}")

    @pytest.fixture
    def storage_client(self, mock_env):
        from google.cloud import storage
        return storage.Client()

    @pytest.fixture
    def bucket(self, storage_client):
        from google.cloud import exceptions
        try:
            return storage_client.create_bucket("dataproduct-apps-topics2")
        except exceptions.Conflict:
            return storage_client.bucket("dataproduct-apps-topics2")

    def test_topics(self, request, settings, bucket, topic, kafka_rest, topic_data, k8s_cluster_data):
        from dataproduct_apps.main import _topic_action
        with unittest.mock.patch("dataproduct_apps.topics.Topic.list") as mock:
            mock.return_value = k8s_cluster_data.topics
            _topic_action(settings)
            assert_bucket_contents(bucket, settings, k8s_cluster_data)
            assert_topic_topic_contents(request, settings, kafka_rest, topic_data)

    def test_collect(self, request, settings, bucket, topic, kafka_rest, topic_data, k8s_cluster_data):
        from dataproduct_apps.main import _collect_action
        with unittest.mock.patch("dataproduct_apps.collect.Application.list") as app_mock:
            app_mock.return_value = k8s_cluster_data.applications
            with unittest.mock.patch("dataproduct_apps.collect.SqlInstance.list") as sql_instance_mock:
                sql_instance_mock.return_value = k8s_cluster_data.sql_instances
                _collect_action(settings)
                assert_app_topic_contents(request, kafka_rest, settings)


def assert_bucket_contents(bucket, settings, k8s_cluster_data):
    blob = bucket.blob(f"topics_{settings.nais_cluster_name}.json")
    assert blob.exists()
    content = json.loads(blob.download_as_bytes())
    assert len(content) == len(k8s_cluster_data.topics)


def assert_topic_topic_contents(request, settings, kafka_rest, topic_data: TopicData):
    resp = kafka_rest.get("topics", headers={"Content-Type": "application/vnd.kafka.v2+json"})
    resp.raise_for_status()
    topics = resp.json()
    assert settings.topic_topic in topics
    comparable_actual = _get_topic_contents(kafka_rest, request, settings.topic_topic)
    assert len(comparable_actual.keys()) == len(topic_data.expected_topics) + len(topic_data.expected_tombstones)
    for expected_topic in topic_data.expected_topics:
        key = expected_topic.key().decode("utf-8")
        assert key in comparable_actual
        actual_topic = Topic.from_dict(comparable_actual[key])
        assert actual_topic == expected_topic
    for key in topic_data.expected_tombstones:
        assert key in comparable_actual
        assert comparable_actual[key] is None


def assert_app_topic_contents(request, kafka_rest, settings):
    resp = kafka_rest.get("topics", headers={"Content-Type": "application/vnd.kafka.v2+json"})
    resp.raise_for_status()
    topics = resp.json()
    assert settings.app_topic in topics
    comparable_actual = _get_topic_contents(kafka_rest, request, settings.app_topic)
    assert comparable_actual


def _get_topic_contents(kafka_rest, request, topic):
    resp = kafka_rest.post(f"consumers/test-consumer-{request.node.originalname}-{datetime.now().isoformat()}",
                           json={"auto.offset.reset": "earliest"})
    print(dump_all(resp).decode("utf-8"))
    resp.raise_for_status()
    consumer_uri = resp.json()["base_uri"]
    print(f"Consumer URI: {consumer_uri}")
    resp = kafka_rest.post(f"{consumer_uri}/subscription", json={"topics": [topic]})
    print(dump_all(resp).decode("utf-8"))
    resp.raise_for_status()
    deadline = datetime.now() + timedelta(seconds=10)
    records = []
    while datetime.now() < deadline:
        resp = kafka_rest.get(f"{consumer_uri}/records")
        print(dump_all(resp).decode("utf-8"))
        resp.raise_for_status()
        records.extend(resp.json())
        if records:
            break
        time.sleep(1)
    comparable_actual = {}
    for r in records:
        key = b64decode(r["key"]).decode("utf-8")
        if r.get("value", ""):
            value = json.loads(b64decode(r["value"]))
        else:
            value = None
        comparable_actual[key] = value
    return comparable_actual
