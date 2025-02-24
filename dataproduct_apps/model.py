import dataclasses
import datetime
import json
import re
from dataclasses import dataclass, field


@dataclass
class App:
    collection_time: datetime.datetime
    cluster: str
    name: str
    team: str
    action_url: str
    namespace: str
    image: str
    ingresses: list[str] = field(default_factory=list)
    uses_token_x: bool = False
    uses_loki_logs: bool = False
    uses_auto_instrumentation: bool = False
    inbound_apps: list[str] = field(default_factory=list)
    outbound_apps: list[str] = field(default_factory=list)
    outbound_hosts: list[str] = field(default_factory=list)
    read_topics: list[str] = field(default_factory=list)
    write_topics: list[str] = field(default_factory=list)
    dbs: list[str] = field(default_factory=list)

    def have_access(self, candidate_ref):
        return bool(re.fullmatch(candidate_ref.name.replace('*', '.*'), self.name)) \
            and bool(re.fullmatch(candidate_ref.namespace.replace('*', '.*'), self.team))

    def key(self):
        return f"{self.cluster}.{self.namespace}.{self.name}".encode("utf-8")


@dataclass(frozen=True)
class AppRef:
    cluster: str = ""
    namespace: str = ""
    name: str = ""

    def __str__(self):
        address = f"{self.cluster}.{self.namespace}.{self.name}"
        return address

    @classmethod
    def from_dict(cls, d):
        return AppRef(**d)


def appref_from_rule(cluster, namespace, rules):
    cluster = rules.cluster if rules.cluster else cluster
    namespace = rules.namespace if rules.namespace else namespace
    name = rules.application
    return AppRef(cluster=cluster, namespace=namespace, name=name)


@dataclass(frozen=True)
class TopicAccessApp:
    pool: str
    team: str
    namespace: str
    topic: str
    access: str
    app: AppRef

    def topic_name(self):
        return f"{self.pool}.{self.namespace}.{self.topic}"

    def key(self):
        return f"{self.pool}.{self.namespace}.{self.topic}.{self.access}.{self.app}".encode("utf-8")

    @classmethod
    def from_dict(cls, d):
        if "app" in d:
            d["app"] = AppRef.from_dict(d["app"])
        return TopicAccessApp(**d)


@dataclass()
class Database():
    resourceID: str  # NOQA
    databaseVersion: str  # NOQA
    tier: str

    def __str__(self):
        return f"{self.resourceID}.{self.databaseVersion}.{self.tier}"


def value_serializer(value):
    try:
        data = dataclasses.asdict(value)
    except TypeError:
        try:
            data = value.as_dict()
        except AttributeError:
            data = value
    if data and "collection_time" in data:
        data["collection_time"] = datetime.datetime.isoformat(data["collection_time"])
    return json.dumps(data).encode("utf-8")


def value_deserializer(bytes):
    return json.loads(bytes.decode("utf-8"))
