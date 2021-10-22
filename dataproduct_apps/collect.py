import datetime
import json
import os
import subprocess
import logging

from dataclasses import dataclass


LOG = logging.getLogger(__name__)


@dataclass
class App:
    collection_time: datetime.datetime
    cluster: str
    name: str
    team: str
    namespace: str


def collect_apps():
    collection_time = datetime.datetime.now()
    cluster = os.getenv("NAIS_CLUSTER_NAME")
    output = subprocess.check_output(["kubectl", "get", "applications.nais.io", "--all-namespaces", "--output", "json"])
    data = json.loads(output)
    for item in data["items"]:
        metadata = item["metadata"]
        team = metadata["labels"].get("team")
        app = App(
            collection_time,
            cluster,
            metadata["name"],
            team,
            metadata["namespace"]
        )
        LOG.info(app)
