import datetime
import logging
import os

from dataproduct_apps.crd import Application, Topic
from dataproduct_apps.model import App, TopicAccessApp, AppRef, appref_from_rule

LOG = logging.getLogger(__name__)


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
        if topic.metadata.name.startswith("kafkarator-canary"):
            continue
        for acl in topic.spec.acl:
            list_of_topic_accesses.append(TopicAccessApp(pool=topic.spec.pool,
                                                         team=topic.metadata.labels.get("team"),
                                                         namespace=topic.metadata.namespace,
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
        for rule in app.spec.accessPolicy.inbound.rules:
            inbound_apps = inbound_apps + [str(appref_from_rule(cluster, metadata.namespace, rule))]
        for rule in app.spec.accessPolicy.outbound.rules:
            outbound_apps.append(str(appref_from_rule(cluster, metadata.namespace, rule)))
        for host in app.spec.accessPolicy.outbound.external:
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
            outbound_apps,
            outbound_hosts
        )

        for topic_access in topic_accesses:
            if app.have_access(topic_access.app):
                if topic_access.access in ["read", "readwrite"]:
                    app.read_topics.append(topic_access.topic_name())
                if topic_access.access in ["write", "readwrite"]:
                    app.write_topics.append(topic_access.topic_name())
        ##remove duplicates
        app.read_topics = list(set(app.read_topics))
        app.write_topics = list(set(app.write_topics))
        app.read_topics.sort()
        app.write_topics.sort()

        yield app
