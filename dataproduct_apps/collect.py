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


class Rules(Model):
    application = Field(str)
    namespace = Field(str)
    cluster = Field(str)


class External(Model):
    host = Field(str)


class Inbound(Model):
    rules = ListField(Rules)


class Outbound(Model):
    external = ListField(External)
    rules = ListField(Rules)


class AccessPolicy(Model):
    inbound = Field(Inbound)
    outbound = Field(Outbound)


class ApplicationSpec(Model):
    image = Field(str)
    ingresses = ListField(str)
    tokenx = Field(TokenX)
    access_policy = Field(AccessPolicy)


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
        uses_token_x = False if app.spec.tokenx is None else app.spec.tokenx.enabled
        inbound_apps = []
        outbound_apps = []
        outbound_hosts = []
        for rule in app.spec.access_policy.inbound.rules:
            inbound_apps = inbound_apps + [get_application(cluster, metadata.namespace, rule)]
        for rule in app.spec.access_policy.outbound.rules:
            outbound_apps.append(get_application(cluster, metadata.namespace, rule))
        for host in app.spec.access_policy.outbound.external:
            outbound_hosts.append(host.host)
        app = App(
            collection_time,
            cluster,
            metadata.name,
            team,
            metadata.namespace,
            app.spec.image,
            app.spec.ingresses,
            uses_token_x,
            inbound_apps,
            outbound_hosts,
            outbound_apps

        )
        yield app


def get_application(cluster, namespace, rules):
    cluster = rules.cluster if rules.cluster else cluster
    namespace = rules.namespace if rules.namespace else namespace
    address = f"{cluster}.{namespace}.{rules.application}"
    return address
