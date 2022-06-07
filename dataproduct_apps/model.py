import dataclasses
import datetime
import json
from dataclasses import dataclass, field


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


def value_serializer(app):
    data = dataclasses.asdict(app)
    data["collection_time"] = datetime.datetime.isoformat(data["collection_time"])
    return json.dumps(data).encode("utf-8")


def value_deserializer(bytes):
    return json.loads(bytes.decode("utf-8"))
