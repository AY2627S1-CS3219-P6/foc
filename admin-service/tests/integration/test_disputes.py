"""Requires ADMIN_TEST_DATABASE_URL: a DISPOSABLE migrated Admin database (admin URL).

Covers the PostgreSQL guarantees behind N2F3.2-N2F3.6 and N2NFR3.1-N2NFR3.5.
"""

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.admin.disputes import (
    IdempotencyKeyReused,
    InvalidTransition,
    ReasonRequired,
    ReportAlreadyOpen,
    VersionConflict,
    request_fingerprint,
)
from app.admin.repository import DisputeRepository
from app.db import Database

pytestmark = pytest.mark.integration


@pytest.fixture
async def database():
    url = os.environ.get("ADMIN_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ADMIN_TEST_DATABASE_URL to a disposable migrated Admin database")
    database = Database(url)
    yield database
    await database.dispose()


@pytest.fixture
def repository(database):
    return DisputeRepository(database.session_context)


async def record(repository, *, actor=None, key=None, description="Nothing arrived."):
    actor, key, order_id = actor or uuid4(), key or uuid4(), uuid4()
    dispute_id, created = await repository.create(
        order_id=order_id,
        description=description,
        evidence_refs=["chat:1"],
        actor=actor,
        key=key,
        fingerprint=request_fingerprint(order_id, description, ["chat:1"]),
        correlation_id="integration",
    )
    return dispute_id, created, actor, key, order_id


async def change(repository, dispute_id, to_status, version, reason=None):
    await repository.transition(
        dispute_id,
        to_status=to_status,
        reason=reason,
        expected_version=version,
        actor=uuid4(),
        correlation_id="integration",
    )


async def test_create_is_idempotent_and_audited(repository):
    actor, key, order_id = uuid4(), uuid4(), uuid4()
    values = dict(
        order_id=order_id,
        description="Nothing arrived.",
        evidence_refs=[],
        actor=actor,
        key=key,
        fingerprint=request_fingerprint(order_id, "Nothing arrived.", []),
        correlation_id="integration",
    )
    dispute_id, created = await repository.create(**values)
    assert created is True
    assert await repository.create(**values) == (dispute_id, False)
    with pytest.raises(IdempotencyKeyReused):
        await repository.create(
            **{**values, "fingerprint": request_fingerprint(order_id, "Different", [])}
        )
    row, events = await repository.dispute(dispute_id)
    assert (row["status"], row["version"]) == ("OPEN", 1)
    assert [event["to_status"] for event in events] == ["OPEN"]
    entries, _ = await repository.audit_page(
        actor_id=actor, target_id=None, outcome=None, page=1, page_size=50
    )
    assert [(entry["action"], entry["outcome"]) for entry in entries] == [
        ("DISPUTE_CREATE", "SUCCESS")
    ]


async def test_workflow_and_rejections_leave_the_dispute_unchanged(repository):
    dispute_id, *_ = await record(repository)
    with pytest.raises(InvalidTransition):
        await change(repository, dispute_id, "RESOLVED", 1, "Refund agreed")
    with pytest.raises(VersionConflict):
        await change(repository, dispute_id, "UNDER_REVIEW", 2)
    row, events = await repository.dispute(dispute_id)
    assert (row["status"], row["version"], len(events)) == ("OPEN", 1, 1)

    await change(repository, dispute_id, "UNDER_REVIEW", 1)
    with pytest.raises(ReasonRequired):
        await change(repository, dispute_id, "RESOLVED", 2)
    await change(repository, dispute_id, "RESOLVED", 2, "Refund agreed with the requester.")
    row, events = await repository.dispute(dispute_id)
    assert (row["status"], row["version"]) == ("RESOLVED", 3)
    assert row["resolution_reason"] == "Refund agreed with the requester."
    assert [(event["from_status"], event["to_status"]) for event in events] == [
        (None, "OPEN"),
        ("OPEN", "UNDER_REVIEW"),
        ("UNDER_REVIEW", "RESOLVED"),
    ]


async def test_concurrent_changes_from_the_same_version_succeed_once(repository):
    dispute_id, *_ = await record(repository)
    results = await asyncio.gather(
        *(change(repository, dispute_id, "UNDER_REVIEW", 1) for _ in range(5)),
        return_exceptions=True,
    )
    assert sum(result is None for result in results) == 1
    assert all(isinstance(result, VersionConflict) for result in results if result is not None)
    row, events = await repository.dispute(dispute_id)
    assert (row["version"], len(events)) == (2, 2)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE admin_service.dispute_events SET reason = 'edited' WHERE dispute_id = :id",
        "DELETE FROM admin_service.dispute_events WHERE dispute_id = :id",
        "UPDATE admin_service.audit_log SET correlation_id = 'edited' WHERE target_id = :id",
        "DELETE FROM admin_service.audit_log WHERE target_id = :id",
        "DELETE FROM admin_service.disputes WHERE id = :id",
        "UPDATE admin_service.disputes SET description = 'edited', status = 'UNDER_REVIEW', "
        "version = version + 1 WHERE id = :id",
        "UPDATE admin_service.disputes SET status = 'RESOLVED', resolution_reason = 'skip', "
        "version = version + 1 WHERE id = :id",
    ],
)
async def test_recorded_history_and_audit_cannot_be_rewritten(database, repository, statement):
    dispute_id, *_ = await record(repository)
    with pytest.raises(DBAPIError):
        async with database.session_context() as session, session.begin():
            await session.execute(text(statement), {"id": dispute_id})


async def test_one_open_report_per_participant_until_it_is_decided(repository):
    reporter, courier, order_id = uuid4(), uuid4(), uuid4()

    async def report(description, who=reporter, role="REQUESTER"):
        return await repository.report(
            order_id=order_id,
            description=description,
            reporter=who,
            role=role,
            key=uuid4(),
            fingerprint=request_fingerprint(order_id, description, []),
            correlation_id="integration",
        )

    dispute_id, created = await report("Nothing arrived.")
    assert created is True
    with pytest.raises(ReportAlreadyOpen):
        await report("Still nothing.")
    await change(repository, dispute_id, "UNDER_REVIEW", 1)
    await change(repository, dispute_id, "REJECTED", 2, "Courier showed delivery photo.")
    second, created = await report("It happened again.")
    assert created is True and second != dispute_id
    rows, total = await repository.reports_for(reporter, page=1, page_size=10)
    assert total == 2 and {row["reporter_role"] for row in rows} == {"REQUESTER"}

    # The other participant may report too; administrator records stay out of participant views.
    await report("Requester gave the wrong building.", who=courier, role="COURIER")
    admin_record = dict(description="Raised by phone.", evidence_refs=[], actor=uuid4())
    await repository.create(
        order_id=order_id,
        key=uuid4(),
        fingerprint=request_fingerprint(order_id, "Raised by phone.", []),
        correlation_id="integration",
        **admin_record,
    )
    rows, total = await repository.reports_about(order_id, page=1, page_size=10)
    assert total == 3
    assert sorted(row["reporter_role"] for row in rows) == ["COURIER", "REQUESTER", "REQUESTER"]


async def test_runtime_role_has_only_the_needed_privileges(database):
    checks = {
        "has_table_privilege('admin_service_app', 'admin_service.disputes', 'DELETE')": False,
        "has_table_privilege('admin_service_app', 'admin_service.dispute_events', 'UPDATE')": False,
        "has_table_privilege('admin_service_app', 'admin_service.audit_log', 'UPDATE')": False,
        "has_table_privilege('admin_service_app', 'admin_service.audit_log', 'INSERT')": True,
        "has_column_privilege('admin_service_app', 'admin_service.disputes', 'status', "
        "'UPDATE')": True,
        "has_column_privilege('admin_service_app', 'admin_service.disputes', 'description', "
        "'UPDATE')": False,
    }
    async with database.session_context() as session:
        for expression, expected in checks.items():
            assert await session.scalar(text(f"SELECT {expression}")) is expected, expression
