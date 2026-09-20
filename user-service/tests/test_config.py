from app.core.config import Settings


def test_blank_database_url_is_treated_as_unconfigured() -> None:
    settings = Settings(_env_file=None, database_url="   ")

    assert settings.database_url is None
