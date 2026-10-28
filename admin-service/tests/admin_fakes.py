"""Test doubles shared by ASGI tests. They never touch a real database or User Service."""

from datetime import UTC, datetime
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
        self.user_id = uuid4()

    async def identity(self, token):
        self.tokens.append(token)
        if self.error is not None:
            raise self.error
        return Principal(user_id=self.user_id, system_role=self.role, account_status="ACTIVE")


class FakeOrders:
    """Stands in for Order's GET /v1/admin/orders/{id}."""

    def __init__(self, known=True, error=None):
        self.known = known
        self.error = error
        self.calls = []

    async def exists(self, order_id, token):
        self.calls.append((order_id, token))
        if self.error is not None:
            raise self.error
        return self.known


def dispute_row(**overrides):
    now = datetime(2026, 10, 28, 4, 0, tzinfo=UTC)
    row = {
        "id": uuid4(),
        "order_id": uuid4(),
        "description": "Courier marked the errand delivered but nothing arrived.",
        "evidence_refs": [],
        "status": "OPEN",
        "resolution_reason": None,
        "created_by": uuid4(),
        "created_at": now,
        "updated_at": now,
        "version": 1,
    }
    return {**row, **overrides}


class FakeDisputes:
    """Records calls and returns scripted results; integration tests cover the SQL itself."""

    def __init__(self):
        self.calls = []
        self.rejections = []
        self.error = None
        self.audit_error = None
        self.created = True
        self.row = None
        self.events = []
        self.page = ([], 0)
        self.audit = ([], 0)

    async def create(self, **values):
        self.calls.append(("create", values))
        if self.error is not None:
            raise self.error
        self.row = dispute_row(
            order_id=values["order_id"],
            description=values["description"],
            evidence_refs=values["evidence_refs"],
            created_by=values["actor"],
        )
        self.events = [
            {
                "sequence": 1,
                "from_status": None,
                "to_status": "OPEN",
                "actor_id": values["actor"],
                "reason": None,
                "occurred_at": self.row["created_at"],
            }
        ]
        return self.row["id"], self.created

    async def transition(self, dispute_id, **values):
        self.calls.append(("transition", dispute_id, values))
        if self.error is not None:
            raise self.error
        self.row = {**self.row, "status": values["to_status"], "version": self.row["version"] + 1}

    async def record_rejection(self, **values):
        if self.audit_error is not None:
            raise self.audit_error
        self.rejections.append(values)

    async def dispute(self, dispute_id):
        if self.row is None or self.row["id"] != dispute_id:
            return None, []
        return self.row, self.events

    async def disputes_page(self, **filters):
        self.calls.append(("disputes_page", filters))
        return self.page

    async def audit_page(self, **filters):
        self.calls.append(("audit_page", filters))
        return self.audit
