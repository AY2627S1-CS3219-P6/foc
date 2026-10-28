"""Short PostgreSQL transactions for disputes, their history and the audit log."""

from uuid import UUID, uuid4

from sqlalchemy import and_, func, insert, select, text, true, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.admin.disputes import (
    FINAL_STATUSES,
    DisputeNotFound,
    IdempotencyKeyReused,
    VersionConflict,
    check_transition,
)
from app.admin.tables import audit_log, dispute_events, disputes


def audit_entry(*, actor, action, target_type, target_id, correlation_id, error_code=None):
    return {
        "id": uuid4(),
        "actor_id": actor,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "outcome": "REJECTED" if error_code else "SUCCESS",
        "error_code": error_code,
        "correlation_id": correlation_id,
    }


class DisputeRepository:
    def __init__(self, sessions):
        self.sessions = sessions

    async def create(
        self, *, order_id, description, evidence_refs, actor, key, fingerprint, correlation_id
    ) -> tuple[UUID, bool]:
        """Record a dispute, its first history entry and its audit entry atomically.

        A replay of the same key and body returns the original dispute (created=False).
        """
        async with self.sessions() as session, session.begin():
            dispute_id = await session.scalar(
                pg_insert(disputes)
                .values(
                    id=uuid4(),
                    order_id=order_id,
                    description=description,
                    evidence_refs=evidence_refs,
                    status="OPEN",
                    created_by=actor,
                    idempotency_key=key,
                    request_hash=fingerprint,
                    version=1,
                )
                .on_conflict_do_nothing(index_elements=["created_by", "idempotency_key"])
                .returning(disputes.c.id)
            )
            if dispute_id is None:
                existing = (
                    await session.execute(
                        select(disputes.c.id, disputes.c.request_hash).where(
                            disputes.c.created_by == actor, disputes.c.idempotency_key == key
                        )
                    )
                ).one()
                if existing.request_hash != fingerprint:
                    raise IdempotencyKeyReused()
                return existing.id, False
            await session.execute(
                insert(dispute_events).values(
                    dispute_id=dispute_id, sequence=1, to_status="OPEN", actor_id=actor
                )
            )
            await session.execute(
                insert(audit_log).values(
                    **audit_entry(
                        actor=actor,
                        action="DISPUTE_CREATE",
                        target_type="DISPUTE",
                        target_id=dispute_id,
                        correlation_id=correlation_id,
                    )
                )
            )
            return dispute_id, True

    async def transition(
        self, dispute_id, *, to_status, reason, expected_version, actor, correlation_id
    ) -> None:
        """Change status, append history and audit in one transaction; rejections roll back."""
        async with self.sessions() as session, session.begin():
            current = (
                await session.execute(
                    select(disputes.c.status, disputes.c.version)
                    .where(disputes.c.id == dispute_id)
                    .with_for_update()
                )
            ).one_or_none()
            if current is None:
                raise DisputeNotFound()
            if current.version != expected_version:
                raise VersionConflict()
            check_transition(current.status, to_status, reason)
            await session.execute(
                update(disputes)
                .where(disputes.c.id == dispute_id, disputes.c.version == expected_version)
                .values(
                    status=to_status,
                    resolution_reason=reason if to_status in FINAL_STATUSES else None,
                    version=disputes.c.version + 1,
                    updated_at=func.clock_timestamp(),
                )
            )
            sequence = await session.scalar(
                select(func.coalesce(func.max(dispute_events.c.sequence), 0) + 1).where(
                    dispute_events.c.dispute_id == dispute_id
                )
            )
            await session.execute(
                insert(dispute_events).values(
                    dispute_id=dispute_id,
                    sequence=sequence,
                    from_status=current.status,
                    to_status=to_status,
                    actor_id=actor,
                    reason=reason,
                )
            )
            await session.execute(
                insert(audit_log).values(
                    **audit_entry(
                        actor=actor,
                        action="DISPUTE_TRANSITION",
                        target_type="DISPUTE",
                        target_id=dispute_id,
                        correlation_id=correlation_id,
                    )
                )
            )

    async def record_rejection(self, **values) -> None:
        """Audit a rejected attempt in its own transaction, after the attempt rolled back."""
        async with self.sessions() as session, session.begin():
            await session.execute(insert(audit_log).values(**audit_entry(**values)))

    async def dispute(self, dispute_id) -> tuple[dict | None, list[dict]]:
        async with self.sessions() as session, session.begin():
            # Read the dispute and its history from one snapshot.
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            row = (
                await session.execute(select(disputes).where(disputes.c.id == dispute_id))
            ).mappings().one_or_none()
            if row is None:
                return None, []
            events = (
                await session.execute(
                    select(dispute_events)
                    .where(dispute_events.c.dispute_id == dispute_id)
                    .order_by(dispute_events.c.sequence)
                )
            ).mappings().all()
            return dict(row), [dict(event) for event in events]

    async def disputes_page(self, *, status, order_id, page, page_size):
        filters = []
        if status is not None:
            filters.append(disputes.c.status == status)
        if order_id is not None:
            filters.append(disputes.c.order_id == order_id)
        return await self._page(
            disputes, filters, (disputes.c.created_at.desc(), disputes.c.id.desc()), page, page_size
        )

    async def audit_page(self, *, actor_id, target_id, outcome, page, page_size):
        filters = []
        if actor_id is not None:
            filters.append(audit_log.c.actor_id == actor_id)
        if target_id is not None:
            filters.append(audit_log.c.target_id == target_id)
        if outcome is not None:
            filters.append(audit_log.c.outcome == outcome)
        return await self._page(
            audit_log,
            filters,
            (audit_log.c.occurred_at.desc(), audit_log.c.id.desc()),
            page,
            page_size,
        )

    async def _page(self, table, filters, ordering, page, page_size):
        condition = and_(*filters) if filters else true()
        async with self.sessions() as session, session.begin():
            # Keep count and page consistent within one request.
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            total = await session.scalar(select(func.count()).select_from(table).where(condition))
            rows = (
                await session.execute(
                    select(table)
                    .where(condition)
                    .order_by(*ordering)
                    .limit(page_size)
                    .offset((page - 1) * page_size)
                )
            ).mappings().all()
            return [dict(row) for row in rows], total
