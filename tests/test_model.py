import dataclasses
import datetime

from dataproduct_apps.model import App, value_deserializer, value_serializer, AppRef

COLLECTION_TIME = datetime.datetime.now()
CLUSTER = "test-cluster"


def test_serdes():
    original = App(COLLECTION_TIME, CLUSTER, "basta", "aura", "default",
                   "ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
                   ["https://basta.nais.preprod.local", "https://basta.dev-fss-pub.nais.io"],
                   [{"app": "app1"}], [{"app": "app2"}])
    expected = dataclasses.asdict(original)
    expected['collection_time'] = expected['collection_time'].isoformat()
    result = value_deserializer(value_serializer(original))
    assert result == expected


def test_have_access():
    app = App(COLLECTION_TIME, CLUSTER, "basta", "aura", "default",
                   "ghcr.io/navikt/basta/basta:2c441d3675781c7254f821ffc5cd8c99fbf1c06a",
                   ["https://basta.nais.preprod.local", "https://basta.dev-fss-pub.nais.io"],
                   [{"app": "app1"}], [{"app": "app2"}])

    assert app.have_access(AppRef(name="*", namespace="aura"))
    assert not app.have_access(AppRef(name="fasit", namespace="aura"))
    assert app.have_access(AppRef(name="bas*", namespace="aura"))
    assert not app.have_access(AppRef(name="fas*", namespace="aura"))


def test_have_access_helse_app():
    app = App(COLLECTION_TIME, CLUSTER, "helse-spleis", "tbd", "tbd", "")
    assert app.have_access(AppRef(name="helse-*", namespace="tbd"))
    assert not app.have_access(AppRef(name="helse-", namespace="tbd"))
    assert not app.have_access(AppRef(name="helse", namespace="tbd"))
    assert app.have_access(AppRef(name="helse*", namespace="tbd"))
    assert not app.have_access(AppRef(name="e*", namespace="tbd"))
    assert not app.have_access(AppRef(name="*helse", namespace="tbd"))
    assert app.have_access(AppRef(name="*helse*", namespace="tbd"))


def test_have_access_helse_namespace():
    app = App(COLLECTION_TIME, CLUSTER, "helse-spleis", "tbd", "tbd", "")
    assert app.have_access(AppRef(name="helse-spleis", namespace="tbd"))
    assert app.have_access(AppRef(name="helse-spleis", namespace="t*"))
    assert app.have_access(AppRef(name="helse-spleis", namespace="*"))
    assert not app.have_access(AppRef(name="helse-spleis", namespace="b*"))
    assert app.have_access(AppRef(name="helse-spleis", namespace="*d"))
    assert app.have_access(AppRef(name="helse-spleis", namespace="*b*"))

