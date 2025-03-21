import datetime

from k8s.models.common import ObjectMeta

from dataproduct_apps.collect import parse_apps
from dataproduct_apps.crd import TokenX, Rules, External, Inbound, Outbound, AccessPolicy, Observability, \
    AutoInstrumentation, Logging, Destination, ApplicationSpec, Application, TopicAccess, TopicSpec, Topic, \
    SqlInstance, SqlInstanceSpec, SqlInstanceSpecSettings
from dataproduct_apps.model import App, TopicAccessApp, AppRef
from dataproduct_apps.topics import parse_topics

TOPIC1 = Topic(
    metadata=ObjectMeta(
        name="topic1",
        namespace="team1",
        labels={"team": "team1"},
    ),
    spec=TopicSpec(
        pool="pool",
        acl=[
            TopicAccess(access="read", application="basta", team="aura"),
        ]
    )
)
TOPIC_KAFKARATOR_CANARY = Topic(
    metadata=ObjectMeta(
        name="kafkarator-canary-prod-gcp",
        namespace="aura",
        labels={"team": "team2"},
    ),
    spec=TopicSpec(
        pool="pool",
        acl=[
            TopicAccess(access="readwrite", application="basta", team="aura"),
            TopicAccess(access="write", application="*", team="aura")
        ]
    )
)

TOPIC2 = Topic(
    metadata=ObjectMeta(
        name="topic2",
        namespace="team2",
        labels={"team": "team2"}
    ),
    spec=TopicSpec(
        pool="pool",
        acl=[
            TopicAccess(access="readwrite", application="basta", team="aura"),
            TopicAccess(access="write", application="*", team="aura")
        ]
    )
)

TOPIC_WITH_NO_LABELS = Topic(
    metadata=ObjectMeta(
        name="topic-with-no-labels",
        namespace="team2",
    ),
    spec=TopicSpec(
        pool="pool",
        acl=[
            TopicAccess(access="readwrite", application="basta", team="aura"),
        ]
    )
)

COLLECTION_TIME = datetime.datetime.now()
CLUSTER = "prod-fss"
TEST_DATA_APPS = [
    Application(
        metadata=ObjectMeta(name="basta", namespace="default", labels={"team": "aura"},
                            annotations={"deploy.nais.io/github-workflow-run-url": "www.vg.no"}),
        spec=ApplicationSpec(image="ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
                             ingresses=["https://basta.nais.preprod.local",
                                        "https://basta.dev-fss-pub.nais.io"],
                             tokenx=TokenX(enabled=True),
                             observability=Observability(autoInstrumentation=AutoInstrumentation(
                                 enabled=True), logging=Logging(destinations=[Destination(id="loki")])),
                             accessPolicy=AccessPolicy(
                                 inbound=Inbound(rules=[
                                     Rules(application="app1"),
                                     Rules(application="app2", namespace="team2", cluster="cluster2")]),
                                 outbound=Outbound(external=[External(host="external-application.example.com")],
                                                   rules=[
                                                       Rules(
                                                           application="app1"),
                                                       Rules(application="app2", namespace="team2",
                                                             cluster="cluster2")])
                             )
                             )
    ),
    Application(
        metadata=ObjectMeta(name="babylon", namespace="aura", labels={"team": "aura"},
                            annotations={"deploy.nais.io/github-workflow-run-url": "www.vg.no"}),
        spec=ApplicationSpec(
            image="ghcr.io/nais/babylon:8aa88acbdbfb6d706e0d4e74c7a7651c79e59108"),
    )
]

TEST_DATA_TOPICS = [
    TOPIC1,
    TOPIC2,
    TOPIC_KAFKARATOR_CANARY,
    TOPIC_WITH_NO_LABELS,
]

TEST_DATA_TOPIC_ACCESS = [
    TopicAccessApp(
        pool="pool",
        team="team1",
        namespace="team1",
        topic="topic1",
        access="read",
        app=AppRef(
            namespace="aura",
            name="basta"
        )
    ),
    TopicAccessApp(
        pool="pool",
        team="team2",
        namespace="team2",
        topic="topic2",
        access="readwrite",
        app=AppRef(
            namespace="aura",
            name="basta"
        )
    ),
    TopicAccessApp(
        pool="pool",
        team="team2",
        namespace="team2",
        topic="topic2",
        access="write",
        app=AppRef(
            namespace="aura",
            name="*"
        )
    ),
    TopicAccessApp(
        pool="pool",
        team="team2",
        namespace="team2",
        topic="topic-with-no-labels",
        access="readwrite",
        app=AppRef(
            namespace="aura",
            name="basta"
        )
    ),
]

TEST_DATA_SQL_INSTANCES = [
    SqlInstance(metadata=ObjectMeta(labels={"app": "basta"}),
                spec=SqlInstanceSpec(databaseVersion="POSTGRES_12",
                                     resourceID="res1",
                                     settings=SqlInstanceSpecSettings(tier="db-f1-micro"))),
    SqlInstance(metadata=ObjectMeta(labels={"app": "babylon"}),
                spec=SqlInstanceSpec(databaseVersion="POSTGRES_14",
                                     resourceID="res2",
                                     settings=SqlInstanceSpecSettings(tier="db-f2-medium")))
]

EXPECTED = [
    App(COLLECTION_TIME, CLUSTER, "basta", "aura", "www.vg.no", "default",
        "ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
        ["https://basta.nais.preprod.local", "https://basta.dev-fss-pub.nais.io"],
        True, True, True,
        ["prod-fss.default.app1", "cluster2.team2.app2"],
        ["prod-fss.default.app1", "cluster2.team2.app2"],
        ["external-application.example.com"],
        ["pool.team1.topic1", "pool.team2.topic-with-no-labels", "pool.team2.topic2"],
        ["pool.team2.topic-with-no-labels", "pool.team2.topic2"],
        dbs=["res1.POSTGRES_12.db-f1-micro"],
        ),
    App(COLLECTION_TIME, CLUSTER, "babylon", "aura", "www.vg.no", "aura",
        "ghcr.io/nais/babylon:8aa88acbdbfb6d706e0d4e74c7a7651c79e59108", [],
        write_topics=["pool.team2.topic2"],
        dbs=["res2.POSTGRES_14.db-f2-medium"],
        ),
]


def test_parse_data():
    actual = list(parse_apps(COLLECTION_TIME, CLUSTER,
                             TEST_DATA_APPS, TEST_DATA_TOPIC_ACCESS, TEST_DATA_SQL_INSTANCES))
    assert EXPECTED == actual


def test_parse_topics():
    actual = parse_topics(TEST_DATA_TOPICS)
    assert TEST_DATA_TOPIC_ACCESS == actual
