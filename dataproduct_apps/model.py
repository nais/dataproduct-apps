import dataclasses
import datetime
import json
from dataclasses import dataclass, field
from collect import app_ref
import re


@dataclass
class App:
    collection_time: datetime.datetime
    cluster: str
    name: str
    team: str
    namespace: str
    image: str
    ingresses: list[str] = field(default_factory=list)
    uses_token_x: bool = False
    inbound_apps: list[str] = field(default_factory=list)
    outbound_apps: list[str] = field(default_factory=list)
    outbound_hosts: list[str] = field(default_factory=list)
    inbound_topics: list[str] = field(default_factory=list)
    outbound_topics: list[str] = field(default_factory=list)

    def have_have_access(self, candidate_ref: app_ref):
        return bool(re.search(candidate_ref.name, self.name)) and bool(re.search(candidate_ref.team, self.team))


@dataclass
class TopicAccessApp:
    pool: str
    team: str
    topic: str
    access: str
    app: app_ref

def value_serializer(app):
    data = dataclasses.asdict(app)
    data["collection_time"] = datetime.datetime.isoformat(data["collection_time"])
    return json.dumps(data).encode("utf-8")


def value_deserializer(bytes):
    return json.loads(bytes.decode("utf-8"))
