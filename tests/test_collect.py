import datetime

from k8s.models.common import ObjectMeta

from dataproduct_apps.collect import parse_apps, Application, ApplicationSpec, TokenX, Inbound, Outbound, AccessPolicy
from dataproduct_apps.model import App

COLLECTION_TIME = datetime.datetime.now()
CLUSTER = "test-cluster"
TEST_DATA = [
    Application(
        metadata=ObjectMeta(name="basta", namespace="default", labels={"team": "aura"}),
        spec=ApplicationSpec(image="ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
                             ingresses=["https://basta.nais.preprod.local",
                                        "https://basta.dev-fss-pub.nais.io"],
                             tokenx=TokenX(enabled=True),
                             accessPolicy=AccessPolicy(
                                 inbound=Inbound(rules=
                                                 [{"application": "app1"},
                                                  {"application": "app2",
                                                   "cluster": "cluster2",
                                                   "namespace": "namespace2"}
                                                  ]),
                                 outbound=Outbound(external=
                                 [
                                     {"host": "external-application.example.com"}
                                 ], rules=[{"application": "app1"},
                                           {"application": "app2",
                                            "cluster": "cluster2",
                                            "namespace": "namespace2"}
                                           ])
                             )
                             )
    ),
    Application(
        metadata=ObjectMeta(name="babylon", namespace="aura", labels={"team": "aura"}),
        spec=ApplicationSpec(image="ghcr.io/nais/babylon:8aa88acbdbfb6d706e0d4e74c7a7651c79e59108"),
    )
]

EXPECTED = [
    App(COLLECTION_TIME, CLUSTER, "basta", "aura", "default",
        "ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
        ["https://basta.nais.preprod.local", "https://basta.dev-fss-pub.nais.io"], True,
        [{"application": "app1"},
         {"application": "app2",
          "cluster": "cluster2",
          "namespace": "namespace2"}
         ], [{"host": "external-application.example.com"}],
        [{"application": "app1"},
         {"application": "app2",
          "cluster": "cluster2",
          "namespace": "namespace2"}
         ]
        ),
    App(COLLECTION_TIME, CLUSTER, "babylon", "aura", "aura",
        "ghcr.io/nais/babylon:8aa88acbdbfb6d706e0d4e74c7a7651c79e59108", []),
]


def test_parse_data():
    actual = list(parse_apps(COLLECTION_TIME, CLUSTER, TEST_DATA))
    assert EXPECTED == actual
