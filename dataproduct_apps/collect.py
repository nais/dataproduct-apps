import datetime
import logging
import os

from k8s.base import Model
from k8s.fields import Field, ListField
from k8s.models.common import ObjectMeta

from dataproduct_apps.model import App

LOG = logging.getLogger(__name__)


class TokenX(Model):
    enabled = Field(bool, False)


class ApplicationSpec(Model):
    image = Field(str)
    ingresses = ListField(str)
    tokenx = Field(TokenX)


class Application(Model):
    class Meta:
        list_url = "/apis/nais.io/v1alpha1/applications"
        url_template = "/apis/nais.io/v1alpha1/namespaces/{namespace}/applications/{name}"

    apiVersion = Field(str, "nais.io/v1alpha1")  # NOQA
    kind = Field(str, "Application")

    metadata = Field(ObjectMeta)
    spec = Field(ApplicationSpec)


def init_k8s_client():
    # TODO: Implement loading from KUBECONFIG for local development
    from k8s import config
    token_file = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    if os.path.exists(token_file):
        with open(token_file) as fobj:
            config.api_token = fobj.read().strip()
    config.verify_ssl = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
    config.api_server = "https://kubernetes.default"


def collect_apps():
    init_k8s_client()
    collection_time = datetime.datetime.now()
    cluster = os.getenv("NAIS_CLUSTER_NAME")
    apps = Application.list(namespace=None)
    LOG.info("Found %d applications in %s", len(apps), cluster)
    yield from parse_apps(collection_time, cluster, apps)


def parse_apps(collection_time, cluster, apps):
    for app in apps:
        metadata = app.metadata
        team = metadata.labels.get("team")
        uses_tokenx = False if app.spec.tokenx is None else app.spec.tokenx.enabled
        app = App(
            collection_time,
            cluster,
            metadata.name,
            team,
            metadata.namespace,
            app.spec.image,
            app.spec.ingresses,
            uses_tokenx
        )
        yield app


