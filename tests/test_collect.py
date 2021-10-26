import datetime

from dataproduct_apps.collect import parse_apps, App

COLLECTION_TIME = datetime.datetime.now()
CLUSTER = "test-cluster"
TEST_DATA = {
    "apiVersion": "v1",
    "items": [
        {
            "apiVersion": "nais.io/v1alpha1",
            "kind": "Application",
            "metadata": {
                "labels": {
                    "team": "aura"
                },
                "name": "babylon",
                "namespace": "aura",
            },
            "spec": {
                "image": "ghcr.io/nais/babylon:8aa88acbdbfb6d706e0d4e74c7a7651c79e59108",
            },
        },
        {
            "apiVersion": "nais.io/v1alpha1",
            "kind": "Application",
            "metadata": {
                "labels": {
                    "team": "aura"
                },
                "name": "basta",
                "namespace": "default",
            },
            "spec": {
                "image": "ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
                "ingresses": [
                    "https://basta.nais.preprod.local",
                    "https://basta.dev-fss-pub.nais.io"
                ],
            },
        },
        {
            "apiVersion": "nais.io/v1alpha1",
            "kind": "Application",
            "metadata": {
                "labels": {
                    "team": "aura"
                },
                "name": "fasit",
                "namespace": "aura",
            },
            "spec": {
                "image": "docker.pkg.github.com/navikt/fasit/fasit:51e2ae52a3f692c1f1fb19ed29f29667b1418795",
                "ingresses": [
                    "https://fasit.nais.preprod.local/conf/",
                    "https://fasit.nais.preprod.local/api",
                    "https://fasit.nais.preprod.local/rest",
                    "https://fasit.dev.intern.nav.no/api"
                ],
            },
        }
    ],
    "kind": "List",
    "metadata": {
        "resourceVersion": "",
        "selfLink": ""
    }
}

EXPECTED = [
    App(COLLECTION_TIME, CLUSTER, "babylon", "aura", "aura",
        "ghcr.io/nais/babylon:8aa88acbdbfb6d706e0d4e74c7a7651c79e59108", []),
    App(COLLECTION_TIME, CLUSTER, "basta", "aura", "default",
        "ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
        ["https://basta.nais.preprod.local", "https://basta.dev-fss-pub.nais.io"]),
    App(COLLECTION_TIME, CLUSTER, "fasit", "aura", "aura",
        "docker.pkg.github.com/navikt/fasit/fasit:51e2ae52a3f692c1f1fb19ed29f29667b1418795", [
            "https://fasit.nais.preprod.local/conf/",
            "https://fasit.nais.preprod.local/api",
            "https://fasit.nais.preprod.local/rest",
            "https://fasit.dev.intern.nav.no/api"
        ]),
]


def test_parse_data():
    actual = list(parse_apps(COLLECTION_TIME, CLUSTER, TEST_DATA))
    assert EXPECTED == actual
