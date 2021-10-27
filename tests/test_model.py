import datetime

from dataproduct_apps.model import App, _value_deserializer, _value_serializer

COLLECTION_TIME = datetime.datetime.now()
CLUSTER = "test-cluster"


def test_serdes():
    original = App(COLLECTION_TIME, CLUSTER, "basta", "aura", "default",
                   "ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
                   ["https://basta.nais.preprod.local", "https://basta.dev-fss-pub.nais.io"])
    result = _value_deserializer(_value_serializer(original))
    assert result == original
