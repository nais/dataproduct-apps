import datetime
import logging
import os
from dataclasses import dataclass, field

from k8s.base import Model
from k8s.fields import Field, ListField
from k8s.models.common import ObjectMeta

LOG = logging.getLogger(__name__)


class ApplicationSpec(Model):
    image = Field(str)
    ingresses = ListField(str)


class Application(Model):
    class Meta:
        list_url = "/apis/nais.io/v1alpha1/applications"
        url_template = "/apis/nais.io/v1alpha1/namespaces/{namespace}/applications/{name}"

    apiVersion = Field(str, "nais.io/v1alpha1")  # NOQA
    kind = Field(str, "Application")

    metadata = Field(ObjectMeta)
    spec = Field(ApplicationSpec)


@dataclass
class App:
    collection_time: datetime.datetime
    cluster: str
    name: str
    team: str
    namespace: str
    image: str
    ingresses: list[str] = field(default_factory=list)


def init_k8s_client():
    # TODO: Implement loading from KUBECONFIG for local development
    from k8s import config
    token_file = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    if os.path.exists(token_file):
        with open(token_file) as fobj:
            config.api_token = fobj.read().strip()
    config.verify_ssl = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
    config.api_server = "https://kubernetes.default.svc.cluster.local"


def collect_apps():
    init_k8s_client()
    collection_time = datetime.datetime.now()
    cluster = os.getenv("NAIS_CLUSTER_NAME")
    apps = Application.list(namespace=None)
    yield from parse_apps(collection_time, cluster, apps)


def parse_apps(collection_time, cluster, apps):
    for app in apps:
        metadata = app.metadata
        team = metadata.labels.get("team")
        app = App(
            collection_time,
            cluster,
            metadata.name,
            team,
            metadata.namespace,
            app.spec.image,
            app.spec.ingresses,
        )
        yield app
