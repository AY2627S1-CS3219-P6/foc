"""Test doubles shared by ASGI tests. They never touch a real database or User Service."""

from uuid import uuid4

from app.admin.schemas import Principal


class NoDatabase:
    async def ping(self):
        return False

    async def dispose(self):
        pass

    def session_context(self):
        raise AssertionError("this test must not open database sessions")


class FakeIdentity:
    """Stands in for User's GET /v1/users/me; records the forwarded tokens."""

    def __init__(self, role="ADMIN", error=None):
        self.role = role
        self.error = error
        self.tokens = []

    async def identity(self, token):
        self.tokens.append(token)
        if self.error is not None:
            raise self.error
        return Principal(user_id=uuid4(), system_role=self.role, account_status="ACTIVE")
