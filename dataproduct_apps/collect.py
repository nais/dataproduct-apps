import datetime
import logging
import os

from k8s.base import Model
from k8s.fields import Field, ListField
from k8s.models.common import ObjectMeta

from dataproduct_apps.model import App, TopicAccessApp, AppRef, appref_from_rule

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


class TopicAccess(Model):
    access = Field(str)
    application = Field(str)
    team = Field(str)


class TopicSpec(Model):
    pool = Field(str)
    acl = ListField(TopicAccess)


class Topic(Model):
    class Meta:
        list_url = "http://localhost:8001/apis/kafka.nais.io/v1/topics"
        url_template = "/apis/nais.io/v1/namespaces/{namespace}/topics/{name}"

    apiVersion = Field(str, "kafka.nais.io/v1")  # NOQA
    kind = Field(str, "Topic")
    metadata = Field(ObjectMeta)
    spec = Field(TopicSpec)


def init_k8s_client():
    # TODO: Implement loading from KUBECONFIG for local development
    from k8s import config
    token_file = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    if os.path.exists(token_file):
        with open(token_file) as fobj:
            config.api_token = fobj.read().strip()
    config.verify_ssl = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
    config.api_server = "https://kubernetes.default"


def collect_data():
    init_k8s_client()
    collection_time = datetime.datetime.now()
    cluster = os.getenv("NAIS_CLUSTER_NAME")
    topics = Topic.list(namespace=None)
    LOG.info("Found %d topics in %s", len(topics), cluster)
    apps = Application.list(namespace=None)
    LOG.info("Found %d applications in %s", len(apps), cluster)
    yield from parse_apps(collection_time, cluster, apps, topics)


def parse_topics(topics):
    list_of_topic_accesses = []
    for topic in topics:
        for acl in topic.spec.acl:
            list_of_topic_accesses.append(TopicAccessApp(pool=topic.spec.pool,
                                                         team=topic.metadata.labels.get("team"),
                                                         topic=topic.metadata.name,
                                                         access=acl.access,
                                                         app=AppRef(namespace=acl.team, name=acl.application)))
    return list_of_topic_accesses


def parse_apps(collection_time, cluster, apps, topics):
    topic_accesses = parse_topics(topics)
    for app in apps:
        metadata = app.metadata
        team = metadata.labels.get("team")
        uses_token_x = False if app.spec.tokenx is None else app.spec.tokenx.enabled
        inbound_apps = []
        outbound_apps = []
        outbound_hosts = []
        for rule in app.spec.access_policy.inbound.rules:
            inbound_apps = inbound_apps + [appref_from_rule(cluster, metadata.namespace, rule).as_string()]
        for rule in app.spec.access_policy.outbound.rules:
            outbound_apps.append(appref_from_rule(cluster, metadata.namespace, rule).as_string())
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

        for topic_access in topic_accesses:
            if app.have_access(topic_access.app):
                if topic_access.access in ["read", "readwrite"]:
                    app.read_topics.append(topic_access.topic_name())
                if topic_access.access in ["write", "readwrite"]:
                    app.write_topics.append(topic_access.topic_name())

        app.read_topics = list(set(app.read_topics))
        app.write_topics = list(set(app.write_topics))
        app.read_topics.sort()
        app.write_topics.sort()

        yield app
