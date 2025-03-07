from typing import Optional

from pydantic import computed_field
from pydantic.types import FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter='_'
    )

    gcp_team_project_id: Optional[str] = ""

    kafka_brokers: str
    kafka_ca_path: Optional[FilePath] = None
    kafka_certificate_path: Optional[FilePath] = None
    kafka_private_key_path: Optional[FilePath] = None
    kafka_security_protocol: str = "SSL"

    nais_client_id: Optional[str] = ""
    nais_cluster_name: Optional[str] = ""

    app_topic: str = "nais.dataproduct-apps"
    topic_topic: str = "nais.dataproduct-apps-topics"

    @computed_field
    def running_in_nais(self) -> bool:
        return bool(self.nais_client_id)
