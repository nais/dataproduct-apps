import datetime

from k8s.models.common import ObjectMeta

from dataproduct_apps.collect import parse_apps, Application, ApplicationSpec, TokenX, Inbound, Outbound, AccessPolicy, \
    Rules, External, Topic, TopicSpec, TopicAccess
from dataproduct_apps.model import App, AppRef

COLLECTION_TIME = datetime.datetime.now()
CLUSTER = "test-cluster"
TEST_DATA_APPS = [
    Application(
        metadata=ObjectMeta(name="basta", namespace="default", labels={"team": "aura"}),
        spec=ApplicationSpec(image="ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
                             ingresses=["https://basta.nais.preprod.local",
                                        "https://basta.dev-fss-pub.nais.io"],
                             tokenx=TokenX(enabled=True),
                             access_policy=AccessPolicy(
                                 inbound=Inbound(rules=[
                                     Rules(application="app1"),
                                     Rules(application="app2", namespace="team2", cluster="cluster2")
                                 ]
                                 ),
                                 outbound=Outbound(external=[External(host="external-application.example.com")],
                                                   rules=[
                                                       Rules(application="app1"),
                                                       Rules(application="app2", namespace="team2",
                                                             cluster="cluster2")
                                                   ])
                             )
                             )
    ),
    Application(
        metadata=ObjectMeta(name="babylon", namespace="aura", labels={"team": "aura"}),
        spec=ApplicationSpec(image="ghcr.io/nais/babylon:8aa88acbdbfb6d706e0d4e74c7a7651c79e59108"),
    )
]

TEST_DATA_TOPICS = [
    Topic(
        metadata=ObjectMeta(name="topic1", namespace="default", labels={"team": "team1"}),
        spec=TopicSpec(
            pool="pool",
            acl=[
                TopicAccess(access="read", application="basta", team="aura"),
            ]
        )
    ),
    Topic(
        metadata=ObjectMeta(name="topic2", namespace="default", labels={"team": "team2"}),
        spec=TopicSpec(
            pool="pool",
            acl=[
                TopicAccess(access="readwrite", application="basta", team="aura"),
                TopicAccess(access="write", application="*", team="aura")
            ]
        )
    )
]

EXPECTED = [
    App(COLLECTION_TIME, CLUSTER, "basta", "aura", "default",
        "ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
        ["https://basta.nais.preprod.local", "https://basta.dev-fss-pub.nais.io"], True,
        ["test-cluster.default.app1",
         "cluster2.team2.app2"],
        ["external-application.example.com"],
        ["test-cluster.default.app1","cluster2.team2.app2"],
        ["pool.team1.topic1", "pool.team2.topic2"],
        ["pool.team2.topic2"]
        ),
    App(COLLECTION_TIME, CLUSTER, "babylon", "aura", "aura",
        "ghcr.io/nais/babylon:8aa88acbdbfb6d706e0d4e74c7a7651c79e59108", [],
        outbound_topics=["pool.team2.topic2"]),
]


def test_parse_data():
    actual = list(parse_apps(COLLECTION_TIME, CLUSTER, TEST_DATA_APPS, TEST_DATA_TOPICS))
    assert EXPECTED == actual
