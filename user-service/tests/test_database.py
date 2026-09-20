from app.db import async_database_url


def test_standard_postgresql_urls_are_normalized_for_asyncpg() -> None:
    assert (
        async_database_url("postgresql://user:password@database.example/service")
        == "postgresql+asyncpg://user:password@database.example/service"
    )
    assert (
        async_database_url("postgres://user:password@database.example/service")
        == "postgresql+asyncpg://user:password@database.example/service"
    )


def test_existing_asyncpg_url_is_unchanged() -> None:
    database_url = "postgresql+asyncpg://user:password@database.example/service"

    assert async_database_url(database_url) == database_url
