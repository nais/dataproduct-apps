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


def _value_serializer(app):
    data = dataclasses.asdict(app)
    data["collection_time"] = datetime.datetime.isoformat(data["collection_time"])
    return json.dumps(data).encode("utf-8")


def _value_deserializer(bytes):
    data = json.loads(bytes)
    data["collection_time"] = datetime.datetime.fromisoformat(data["collection_time"])
    return App(**data)
