import pytest
from pydantic import SecretStr, ValidationError

from vmarket_ai.settings import ConfigurationError, Settings, load_settings


def test_fake_needs_no_env_or_key():
    settings = Settings(_env_file=None)
    assert settings.provider_mode == "fake"
    assert not settings.live_enabled


@pytest.mark.parametrize(
    "options",
    [
        {"provider_mode": "live"},
        {"qa_enabled": True},
        {
            "qa_enabled": True,
            "private_container": True,
            "bind_host": "0.0.0.0",
            "database_url": "postgresql+psycopg://demo:demo@localhost/vmarket_ai",
        },
        {
            "qa_enabled": True,
            "database_url": "postgresql+psycopg://demo:demo@localhost/vmarket_ai",
            "qa_embedding_mode": "local",
        },
        {"provider_mode": "live", "live_enabled": True},
        {"provider_mode": "live", "live_enabled": True, "openrouter_api": "sentinel-key"},
        {"mode": "integrated"},
        {"bind_host": "0.0.0.0"},
        {"database_url": "postgresql+psycopg://user:sentinel-password@localhost/vmarket"},
        {"database_url": "mysql://user:sentinel-password@localhost/vmarket_ai"},
    ],
)
def test_unsafe_or_incomplete_configuration_rejected(options):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **options)


def test_supported_private_container_is_explicit():
    assert Settings(_env_file=None, bind_host="0.0.0.0", private_container=True).private_container


def test_startup_error_does_not_include_env_values(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AI_DATABASE_URL", "mysql://user:sentinel-password@localhost/vmarket_ai")
    with pytest.raises(ConfigurationError) as exc:
        load_settings()
    assert "sentinel-password" not in str(exc.value)
    assert exc.value.__suppress_context__


def test_secret_fields_not_in_settings_repr():
    settings = Settings(_env_file=None, openrouter_api=SecretStr("sentinel-key"))
    assert "sentinel-key" not in repr(settings)
