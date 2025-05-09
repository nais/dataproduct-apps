import json

from k8s.base import Model
from k8s.fields import Field, ListField
from k8s.models.common import ObjectMeta


class TokenX(Model):
    enabled = Field(bool, False)


class AutoInstrumentation(Model):
    enabled = Field(bool, False)
    runtime = Field(str, "")


class Destination(Model):
    id = Field(str)


class Logging(Model):
    destinations = ListField(Destination)


class Observability(Model):
    autoInstrumentation = Field(AutoInstrumentation)  # NOQA
    logging = Field(Logging)


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
    accessPolicy = Field(AccessPolicy)  # NOQA
    observability = Field(Observability)


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
        list_url = "/apis/kafka.nais.io/v1/topics"
        url_template = "/apis/nais.io/v1/namespaces/{namespace}/topics/{name}"

    apiVersion = Field(str, "kafka.nais.io/v1")  # NOQA
    kind = Field(str, "Topic")
    metadata = Field(ObjectMeta)
    spec = Field(TopicSpec)

    def key(self, collection_cluster):
        return f"{collection_cluster}:{self.spec.pool}:{self.metadata.namespace}:{self.metadata.name}".encode("utf-8")

    def __hash__(self):
        return hash(json.dumps(self.as_dict()))


class SqlInstanceSpecSettings(Model):
    tier = Field(str)


class SqlInstanceSpec(Model):
    databaseVersion = Field(str)  # NOQA
    resourceID = Field(str)  # NOQA
    settings = Field(SqlInstanceSpecSettings)


class SqlInstance(Model):
    class Meta:
        list_url = "/apis/sql.cnrm.cloud.google.com/v1beta1/sqlinstances"
        url_template = "/apis/sql.cnrm.cloud.google.com/v1beta1/namespaces/{namespace}/sqlinstances/{name}"

    metadata = Field(ObjectMeta)
    spec = Field(SqlInstanceSpec)
