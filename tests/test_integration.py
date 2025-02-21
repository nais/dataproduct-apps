import dataclasses
import json
import time
import unittest
from base64 import b64decode, b64encode
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
from dataproduct_apps.model import TopicAccessApp, AppRef

POOL = "dev-nais-local"
TAA_T1_N1_A1_R = TopicAccessApp(pool=POOL, team="namespace1", namespace="namespace1", topic="topic1",
                                access="read", app=AppRef(namespace="namespace1", name="app1"))
TAA_T2_N1_A1_W = TopicAccessApp(pool=POOL, team="namespace2", namespace="namespace2", topic="topic2",
                                access="write", app=AppRef(namespace="namespace1", name="app1"))
TAA_T2_N1_A1_R = TopicAccessApp(pool=POOL, team="namespace2", namespace="namespace2", topic="topic2",
                                access="read", app=AppRef(namespace="namespace1", name="app1"))
TAA_T2_N2_A2_W = TopicAccessApp(pool=POOL, team="namespace2", namespace="namespace2", topic="topic2",
                                access="write", app=AppRef(namespace="namespace2", name="app2"))
TAA_T3_N1_A1_RW = TopicAccessApp(pool=POOL, team="namespace3", namespace="namespace3", topic="topic3",
                                 access="readwrite", app=AppRef(namespace="namespace1", name="app1"))
TAA_T3_N2_A2_RW = TopicAccessApp(pool=POOL, team="namespace3", namespace="namespace3", topic="topic3",
                                 access="readwrite", app=AppRef(namespace="namespace2", name="app2"))

PRE_EXISTING_TOPIC_ACCESSES = [
    TAA_T1_N1_A1_R,
    TAA_T2_N1_A1_R,
    TAA_T2_N1_A1_W,
    TAA_T3_N2_A2_RW,
]

EXPECTED_TOPIC_ACCESSES = [
    TAA_T1_N1_A1_R,
    TAA_T2_N1_A1_R,
    TAA_T2_N2_A2_W,
    TAA_T3_N1_A1_RW,
]

EXPECTED_TOPIC_ACCESS_TOMBSTONES = [
    TAA_T2_N1_A1_W.key(),
    TAA_T3_N2_A2_RW.key(),
]

TEST_HOST = "localhost"
STORAGE_PORT = 9023
KAFKA_PORT = 9092
KAFKA_REST_PORT = 8082
BUCKET = "dataproduct-apps-topics2"


class K8sClusterData(Model):
    topics = ListField(Topic)
    applications = ListField(Application)
    sql_instances = ListField(SqlInstance)


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
    @pytest.fixture(scope="session")
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

    @pytest.fixture(scope="session")
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

    @pytest.fixture(scope="session")
    def kafka_rest(self):
        return KafkaRest()

    @pytest.fixture(scope="session")
    def topic_accesses(self, topic, kafka_rest, settings):
        for taa in PRE_EXISTING_TOPIC_ACCESSES:
            resp = kafka_rest.post(f"topics/{settings.topic_topic}", json={
                "records": [
                    {
                        "key": b64encode(taa.key()).decode("utf-8"),
                        "value": b64encode(json.dumps(dataclasses.asdict(taa)).encode("utf-8")).decode("utf-8"),
                    }
                ]
            })
            resp.raise_for_status()

    @pytest.fixture
    def k8s_cluster_data(self, request):
        data_file = request.path.parent / "integration_test_data" / "k8s_cluster.yaml"
        with open(data_file) as f:
            data = yaml.safe_load(f)
            return K8sClusterData.from_dict(data)

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

    @pytest.mark.parametrize("component", ["topics", "collect"])
    def test_integration(self, request, bucket, topic, kafka_rest, topic_accesses, settings, k8s_cluster_data,
                         component):
        test_func = getattr(self, f"_test_{component}")
        test_func(request, bucket, topic, kafka_rest, topic_accesses, settings, k8s_cluster_data)

    @staticmethod
    def _test_topics(request, bucket, topic, kafka_rest, topic_accesses, settings, k8s_cluster_data):
        from dataproduct_apps.main import _topic_action
        with unittest.mock.patch("dataproduct_apps.topics.Topic.list") as mock:
            mock.return_value = k8s_cluster_data.topics
            _topic_action(settings)
            _assert_bucket_contents(bucket, settings, k8s_cluster_data)
            _assert_topic_topic_contents(request, kafka_rest, settings)

    @staticmethod
    def _test_collect(request, bucket, topic, kafka_rest, topic_accesses, settings, k8s_cluster_data):
        from dataproduct_apps.main import _collect_action
        with unittest.mock.patch("dataproduct_apps.collect.Application.list") as app_mock:
            app_mock.return_value = k8s_cluster_data.applications
            with unittest.mock.patch("dataproduct_apps.collect.SqlInstance.list") as sql_instance_mock:
                sql_instance_mock.return_value = k8s_cluster_data.sql_instances
                _collect_action(settings)
                _assert_app_topic_contents(request, kafka_rest, settings)


def _assert_bucket_contents(bucket, settings, k8s_cluster_data):
    blob = bucket.blob(f"topics_{settings.nais_cluster_name}.json")
    assert blob.exists()
    content = json.loads(blob.download_as_bytes())
    assert len(content) == len(k8s_cluster_data.topics)


def _assert_topic_topic_contents(request, kafka_rest, settings):
    resp = kafka_rest.get("topics", headers={"Content-Type": "application/vnd.kafka.v2+json"})
    resp.raise_for_status()
    topics = resp.json()
    assert settings.topic_topic in topics
    comparable_actual = _get_topic_contents(kafka_rest, request, settings.topic_topic)
    assert len(comparable_actual.keys()) == len(EXPECTED_TOPIC_ACCESSES) + len(EXPECTED_TOPIC_ACCESS_TOMBSTONES)
    for t in EXPECTED_TOPIC_ACCESSES:
        assert t.key() in comparable_actual
        assert comparable_actual[t.key()] == dataclasses.asdict(t)
    for t in EXPECTED_TOPIC_ACCESS_TOMBSTONES:
        assert t in comparable_actual
        assert comparable_actual[t] is None


def _assert_app_topic_contents(request, kafka_rest, settings):
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
        key = b64decode(r["key"])
        if r.get("value", ""):
            value = json.loads(b64decode(r["value"]))
        else:
            value = None
        comparable_actual[key] = value
    return comparable_actual
