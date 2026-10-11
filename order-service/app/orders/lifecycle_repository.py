"""Serialize lifecycle decisions per order; no network calls while locks are held."""

from uuid import UUID, uuid4

from sqlalchemy import func, insert, select, update

from app.orders.errors import not_found
from app.orders.lifecycle import Action, transition_values
from app.orders.tables import history, orders, outbox


class LifecycleRepository:
    def __init__(self, sessions):
        self.sessions = sessions

    async def transition(self, order_id: UUID, actor: UUID, action: Action):
        async with self.sessions() as session, session.begin():
            result = await session.execute(
                select(orders).where(orders.c.id == order_id).with_for_update()
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise not_found()
            # transaction_timestamp() would permit a pre-deadline waiter to win too late.
            now = await session.scalar(select(func.clock_timestamp()))
            values = transition_values(row, actor, action, now)
            if not values:
                return row
            return await self._record(session, row, values, actor, now)

    async def expire_batch(self, limit: int) -> int:
        async with self.sessions() as session, session.begin():
            result = await session.execute(
                select(orders)
                .where(orders.c.state == "OPEN", orders.c.acceptance_deadline <= func.now())
                .order_by(orders.c.acceptance_deadline, orders.c.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
            rows = list(result.mappings())
            for row in rows:
                now = await session.scalar(select(func.clock_timestamp()))
                await self._record(session, row, {"state": "EXPIRED", "expired_at": now}, None, now)
            return len(rows)

    async def _record(self, session, row, values, actor, now):
        updated = await session.execute(
            update(orders)
            .where(orders.c.id == row["id"])
            .values(**values, updated_at=now)
            .returning(orders)
        )
        sequence = await session.scalar(
            select(func.coalesce(func.max(history.c.sequence), 0) + 1).where(
                history.c.order_id == row["id"]
            )
        )
        await session.execute(
            insert(history).values(
                order_id=row["id"],
                sequence=sequence,
                previous_state=row["state"],
                new_state=values["state"],
                actor_id=actor,
                actor_type="SYSTEM" if actor is None else "USER",
                occurred_at=now,
            )
        )
        if values["state"] in ("CANCELLED", "EXPIRED"):
            await session.execute(
                insert(outbox).values(
                    event_id=uuid4(),
                    event_type=f"order.{values['state'].lower()}.v1",
                    order_id=row["id"],
                    reservation_id=row["reservation_id"],
                    occurred_at=now,
                    state="PENDING",
                    publish_attempts=0,
                    next_attempt_at=now,
                )
            )
        return updated.mappings().one()
