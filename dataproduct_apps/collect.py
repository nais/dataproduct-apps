import datetime
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field

LOG = logging.getLogger(__name__)


@dataclass
class App:
    collection_time: datetime.datetime
    cluster: str
    name: str
    team: str
    namespace: str
    image: str
    ingresses: list[str] = field(default_factory=list)


def collect_apps():
    collection_time = datetime.datetime.now()
    cluster = os.getenv("NAIS_CLUSTER_NAME")
    cmd = ["kubectl", "get", "applications.nais.io", "--all-namespaces", "--output", "json"]
    output = execute(cmd)
    data = json.loads(output)
    yield from parse_apps(collection_time, cluster, data)


def parse_apps(collection_time, cluster, data):
    for item in data["items"]:
        metadata = item["metadata"]
        team = metadata["labels"].get("team")
        app = App(
            collection_time,
            cluster,
            metadata["name"],
            team,
            metadata["namespace"],
            item["spec"]["image"],
            item["spec"].get("ingresses", []),
        )
        yield app


def execute(cmd):
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        LOG.error("Calling command '%s' failed: %s\nstdout from call:\n%s\nstderr from call:\n%s",
                  " ".join(cmd), e, e.stdout, e.stderr)
        raise
    return output
