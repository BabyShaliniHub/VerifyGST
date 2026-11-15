import pytest

from app.core.settings import Settings
from app.db.session import IntegrationState, build_url, check_database

SECRET = "s3cret-value"


def unreachable_settings(**overrides) -> Settings:
    values = dict(postgres_host="127.0.0.1", postgres_port=59999, postgres_password=SECRET)
    values.update(overrides)
    return Settings(**values)


def skip_if_postgres_is_down():
    if check_database().state is IntegrationState.UNAVAILABLE:
        pytest.skip("PostgreSQL is not running. Start it with: docker compose up -d")


def test_the_password_is_hidden_from_printed_settings_and_urls():
    settings = unreachable_settings()
    assert SECRET not in repr(settings)
    assert SECRET not in str(settings)
    assert SECRET not in str(build_url(settings))
    assert build_url(settings).password == SECRET


def test_a_missing_password_is_reported_as_not_configured():
    result = check_database(unreachable_settings(postgres_password=""))
    assert result.state is IntegrationState.NOT_CONFIGURED


def test_an_unreachable_database_is_unavailable_and_the_result_leaks_nothing():
    result = check_database(unreachable_settings())
    assert result.state is IntegrationState.UNAVAILABLE
    for secret_text in (SECRET, "59999", "127.0.0.1"):
        assert secret_text not in result.detail


def test_the_local_database_accepts_the_settings_from_env():
    skip_if_postgres_is_down()
    result = check_database()
    assert result.state is IntegrationState.CONNECTED, result.detail


def test_a_wrong_password_is_refused_and_reported_as_authentication_failed():
    skip_if_postgres_is_down()
    result = check_database(Settings(postgres_password="definitely-not-the-password"))
    assert result.state is IntegrationState.AUTHENTICATION_FAILED, result.detail
