import datetime
import json
import logging
import pprint

from dataproduct_apps.config import Settings
from dataproduct_apps.crd import Application, Topic, SqlInstance
from dataproduct_apps.k8s import init_k8s_client
from dataproduct_apps.model import App, Database, appref_from_rule
from dataproduct_apps.topics import parse_topics, get_existing_topics

LOG = logging.getLogger(__name__)


def _format_dataproduct_topic(topics: set[Topic]):
    for topic in topics:
        if topic.metadata.name == "dataproduct-apps":
            return pprint.pformat(topic.as_dict())
    LOG.warning("Could not find dataproduct-apps topic in list, selecting random topic")
    return pprint.pformat(next(iter(topics)).as_dict())


def _compare_topics(topics_from_bucket, topics_from_topic):
    from_bucket = set(topics_from_bucket)
    from_topic = set(topics_from_topic)
    if from_bucket == from_topic:
        LOG.info("Topics are in sync between bucket and topic |o|")
    else:
        LOG.warning("Topics are NOT in sync between bucket and topic :(")
        LOG.info("Number of topics in bucket: %d", len(from_bucket))
        LOG.info("Number of topics in topic: %d", len(from_topic))
        LOG.info("Example topic from bucket: %s", _format_dataproduct_topic(from_bucket))
        LOG.info("Example topic from topic: %s", _format_dataproduct_topic(from_topic))


def collect_data(settings: Settings):
    init_k8s_client()
    collection_time = datetime.datetime.now()
    cluster = settings.nais_cluster_name
    topics_from_bucket = read_topics_from_cloud_storage(cluster)
    LOG.info("Found %d topics in %s (from bucket)", len(topics_from_bucket), cluster)
    topics_from_topic = _get_relevant_topics(settings)
    _compare_topics(topics_from_bucket, topics_from_topic)
    sql_instances = [] if "fss" in cluster else SqlInstance.list(
        namespace=None)
    LOG.info("Found %d sql instances in %s", len(sql_instances), cluster)
    apps = Application.list(namespace=None)
    LOG.info("Found %d applications in %s", len(apps), cluster)
    topic_accesses = parse_topics(topics_from_bucket)
    yield from parse_apps(collection_time, cluster, apps, topic_accesses, sql_instances)


def _get_relevant_topics(settings):
    prefix = f"{settings.nais_cluster_name}:".encode("utf-8")
    for k, v in get_existing_topics(settings).items():
        if k.startswith(prefix):
            yield v


def topics_from_json(json_data) -> list[Topic]:
    new_list_of_topics = []
    for new_topic in json.loads(json_data):
        new_list_of_topics.append(Topic.from_dict(new_topic))

    return new_list_of_topics


def read_topics_from_cloud_storage(cluster) -> list[Topic]:
    from google.cloud import storage
    storage_client = storage.Client()
    bucket = storage_client.get_bucket('dataproduct-apps-topics2')
    list_of_topics = []
    blobs = bucket.list_blobs()
    n = 0
    for blob in blobs:
        n = n + 1
        if is_same_env(blob.name, cluster):
            topics = topics_from_json(blob.download_as_string())
            LOG.info("Found %d topics in %s", len(topics), blob.name)
            list_of_topics.extend(topics)

    LOG.info("Read %d files from bucket %s", n, bucket)

    return list_of_topics


def is_same_env(filename, clustername):
    if 'prod' in clustername and 'prod' in filename:
        return True
    if 'dev' in clustername and 'dev' in filename:
        return True
    return False


def databases_owned_by(application, sql_instances):
    matching_dbs = []
    for inst in sql_instances:
        if inst.metadata.labels["app"] == application.metadata.name:
            matching_dbs.append(Database(resourceID=inst.spec.resourceID,
                                         databaseVersion=inst.spec.databaseVersion,
                                         tier=inst.spec.settings.tier))
    return matching_dbs


def parse_apps(collection_time, cluster, applications, topic_accesses, sql_instances):
    total = len(applications)
    LOG.info("Parsing %d applications", total)
    for i, application in enumerate(applications):
        if i % 100 == 0:
            LOG.info("Parsing application %d/%d", i, total)
        metadata = application.metadata
        team = metadata.labels.get("team")
        if metadata.annotations is not None:
            action_url = metadata.annotations.get("deploy.nais.io/github-workflow-run-url")
        else:
            action_url = None

        uses_token_x = False if application.spec.tokenx is None else application.spec.tokenx.enabled

        uses_auto_instrumentation = False
        if application.spec.observability is not None \
                and application.spec.observability.autoInstrumentation is not None:
            uses_auto_instrumentation = bool(
                application.spec.observability.autoInstrumentation.enabled)

        uses_loki_logs = False
        if application.spec.observability is not None \
                and application.spec.observability.logging is not None:
            destinations = application.spec.observability.logging.destinations or []
            for destination in destinations:
                if destination.id == "loki":
                    uses_loki_logs = True
                    break

        databases = [str(db)
                     for db in databases_owned_by(application, sql_instances)]
        inbound_apps = _collect_inbound_apps(application, cluster, metadata)
        outbound_apps = _collect_outbound_apps(application, cluster, metadata)
        outbound_hosts = _collect_outbound_hosts(application)

        app = App(
            collection_time=collection_time,
            cluster=cluster,
            name=metadata.name,
            team=team,
            action_url=action_url,
            namespace=metadata.namespace,
            image=application.spec.image,
            ingresses=application.spec.ingresses,
            uses_token_x=uses_token_x,
            uses_auto_instrumentation=uses_auto_instrumentation,
            uses_loki_logs=uses_loki_logs,
            inbound_apps=inbound_apps,
            outbound_apps=outbound_apps,
            outbound_hosts=outbound_hosts,
            dbs=databases,
        )

        _update_kafka_topics(app, topic_accesses)

        yield app


def _update_kafka_topics(app, topic_accesses):
    read_topics = set()
    write_topics = set()
    for topic_access in topic_accesses:
        if app.have_access(topic_access.app):
            if topic_access.access in ["read", "readwrite"]:
                read_topics.add(topic_access.topic_name())
            if topic_access.access in ["write", "readwrite"]:
                write_topics.add(topic_access.topic_name())
    app.read_topics = list(sorted(read_topics))
    app.write_topics = list(sorted(write_topics))


def _collect_outbound_hosts(app):
    outbound_hosts = []
    for host in app.spec.accessPolicy.outbound.external:
        if host.host is not None:
            outbound_hosts.append(host.host)
    return outbound_hosts


def _collect_outbound_apps(app, cluster, metadata):
    outbound_apps = []
    for rule in app.spec.accessPolicy.outbound.rules:
        outbound_apps.append(
            str(appref_from_rule(cluster, metadata.namespace, rule)))
    return outbound_apps


def _collect_inbound_apps(app, cluster, metadata):
    inbound_apps = []
    for rule in app.spec.accessPolicy.inbound.rules:
        inbound_apps.append(
            str(appref_from_rule(cluster, metadata.namespace, rule)))
    return inbound_apps
