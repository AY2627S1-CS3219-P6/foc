"""One-shot demo-only login provisioning, after canonical SQL initialization."""
import asyncio
import os

import asyncpg


async def main():
    connection = await asyncpg.connect(
        host="database", database="postgres", user="postgres", password=os.environ["DB_PASSWORD"]
    )
    try:
        password = os.environ["APP_PASSWORD"]
        if not password.isalnum():
            raise ValueError("Use generated hexadecimal demo passwords")
        exists = await connection.fetchval("SELECT 1 FROM pg_roles WHERE rolname='order_demo_app'")
        if not exists:
            await connection.execute(f"CREATE ROLE order_demo_app LOGIN PASSWORD '{password}'")
        await connection.execute("GRANT order_service_app TO order_demo_app")
    finally:
        await connection.close()


asyncio.run(main())
