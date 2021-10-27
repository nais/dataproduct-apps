import dataclasses
import datetime

from dataproduct_apps.model import App, value_deserializer, value_serializer

COLLECTION_TIME = datetime.datetime.now()
CLUSTER = "test-cluster"


def test_serdes():
    original = App(COLLECTION_TIME, CLUSTER, "basta", "aura", "default",
                   "ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
                   ["https://basta.nais.preprod.local", "https://basta.dev-fss-pub.nais.io"])
    expected = dataclasses.asdict(original)
    expected['collection_time'] = expected['collection_time'].isoformat()
    result = value_deserializer(value_serializer(original))
    assert result == expected
