import dataclasses

from k8s.models.common import ObjectMeta

from dataproduct_apps.crd import Topic, TopicSpec, TopicAccess
from dataproduct_apps.kafka import value_deserializer, value_serializer
from dataproduct_apps.model import App
from tests.test_model import COLLECTION_TIME, CLUSTER


def test_serdes_application():
    original = App(COLLECTION_TIME, CLUSTER, "basta", "aura", "default",
                   "ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
                   ["https://basta.nais.preprod.local", "https://basta.dev-fss-pub.nais.io"],
                   [{"app": "app1"}], [{"app": "app2"}])
    expected = dataclasses.asdict(original)
    expected['collection_time'] = expected['collection_time'].isoformat()
    result = value_deserializer(value_serializer(original))
    assert result == expected


def test_serdes_topic():
    original = Topic(
        metadata=ObjectMeta(
            namespace="namespace1",
            name="topic1",
        ),
        spec=TopicSpec(
            pool="dev-nais-local",
            acl=[
                TopicAccess(
                    access="read",
                    application="app1",
                    team="team1",
                ),
                TopicAccess(
                    access="write",
                    application="app2",
                    team="team2",
                ),
            ],
        ),
    )
    expected = original.as_dict()
    result = value_deserializer(value_serializer(original))
    assert result == expected


def test_serdes_none():
    original = None
    result = value_deserializer(value_serializer(original))
    assert result is None
