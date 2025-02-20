from pathlib import PosixPath

import pytest

GCP_TEAM_PROJECT_ID = "project"
OVERRIDE_KAFKA_BROKERS = "kafka:9092"
DEFAULT_KAFKA_BROKERS = "localhost:9092"
KAFKA_CA_PATH = __file__
KAFKA_SECURITY_PROTOCOL = "PLAINTEXT"
NAIS_CLIENT_ID = "nais-client-id"
NAIS_CLUSTER_NAME = "dev-nais-local"


class TestConfig:
    @pytest.fixture
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("GCP_TEAM_PROJECT_ID", GCP_TEAM_PROJECT_ID)
        monkeypatch.setenv("KAFKA_BROKERS", OVERRIDE_KAFKA_BROKERS)
        monkeypatch.setenv("KAFKA_CA_PATH", KAFKA_CA_PATH)
        monkeypatch.setenv("KAFKA_SECURITY_PROTOCOL", KAFKA_SECURITY_PROTOCOL)
        monkeypatch.setenv("NAIS_CLIENT_ID", NAIS_CLIENT_ID)
        monkeypatch.setenv("NAIS_CLUSTER_NAME", NAIS_CLUSTER_NAME)

    def test_config_override(self, mock_env):
        from dataproduct_apps.config import Settings
        settings = Settings(_env_file=None)
        assert settings.gcp_team_project_id == GCP_TEAM_PROJECT_ID
        assert settings.kafka_brokers == OVERRIDE_KAFKA_BROKERS
        assert settings.kafka_ca_path == PosixPath(KAFKA_CA_PATH)
        assert settings.kafka_security_protocol == KAFKA_SECURITY_PROTOCOL
        assert settings.nais_client_id == NAIS_CLIENT_ID
        assert settings.nais_cluster_name == NAIS_CLUSTER_NAME
        assert settings.running_in_nais is True

    def test_config_default(self, monkeypatch):
        monkeypatch.setenv("KAFKA_BROKERS", DEFAULT_KAFKA_BROKERS)
        from dataproduct_apps.config import Settings
        settings = Settings(_env_file=None)
        assert settings.gcp_team_project_id == ""
        assert settings.kafka_brokers == DEFAULT_KAFKA_BROKERS
        assert settings.kafka_ca_path is None
        assert settings.kafka_security_protocol == "SSL"
        assert settings.nais_client_id == ""
        assert settings.nais_cluster_name == ""
        assert settings.running_in_nais is False
