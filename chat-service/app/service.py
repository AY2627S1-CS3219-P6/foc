"""Transaction boundary for private conversations. PostgreSQL is authoritative."""

import hashlib
from uuid import uuid4

from sqlalchemy import text

from app.errors import ApiError, not_found, unavailable


def pair(a, b):
    if a == b:
        raise ApiError(422, "INVALID_RECIPIENT", "Choose another user.")
    return tuple(sorted((a, b)))


async def lock(session, namespace, *ids):
    key = int.from_bytes(
        hashlib.blake2b(
            (namespace + ":" + ":".join(map(str, ids))).encode(), digest_size=8
        ).digest(),
        signed=True,
    )
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def message(row):
    return {
        "messageId": str(row["id"]),
        "conversationId": str(row["conversation_id"]),
        "senderUserId": str(row["sender_id"]),
        "clientMessageId": str(row["client_message_id"]),
        "sequence": row["sequence"],
        "text": row["text"],
        "createdAt": row["created_at"].isoformat(),
    }


async def member(session, conversation_id, user_id, for_update=False):
    result = await session.execute(
        text(
            """
        SELECT c.*, p.last_read_sequence FROM chat_service.conversations c
        JOIN chat_service.conversation_participants p ON p.conversation_id = c.id
        WHERE c.id = :cid AND p.user_id = :uid
    """
            + (" FOR UPDATE OF c" if for_update else "")
        ),
        {"cid": conversation_id, "uid": user_id},
    )
    row = result.mappings().first()
    if row is None:
        raise not_found()
    return row


async def blocked(session, low, high):
    return bool(
        (
            await session.execute(
                text("""
        SELECT EXISTS(SELECT 1 FROM chat_service.blocks
          WHERE (blocker_id = :a AND blocked_id = :b)
             OR (blocker_id = :b AND blocked_id = :a))
    """),
                {"a": low, "b": high},
            )
        ).scalar_one()
    )


def other(row, user_id):
    return row["user_high"] if row["user_low"] == user_id else row["user_low"]


class ChatService:
    def __init__(self, database, identity):
        self.db, self.identity = database, identity

    async def active(self, ids):
        people = await self.identity.participants(ids)
        if any(i not in people or people[i]["accountStatus"] != "ACTIVE" for i in ids):
            raise ApiError(409, "RECIPIENT_UNAVAILABLE", "Messaging is unavailable for this user.")
        return people

    async def create(self, user_id, recipient_id):
        low, high = pair(user_id, recipient_id)
        async with self.db.transaction() as session:
            await lock(session, "pair", low, high)
            existing = (
                await session.execute(
                    text("""
                SELECT id FROM chat_service.conversations WHERE user_low=:a AND user_high=:b
            """),
                    {"a": low, "b": high},
                )
            ).scalar_one_or_none()
            if existing:
                return {"conversationId": str(existing)}
            await self.active([user_id, recipient_id])
            if await blocked(session, low, high):
                raise ApiError(409, "MESSAGING_BLOCKED", "Messaging is blocked for this pair.")
            cid = uuid4()
            await session.execute(
                text("""INSERT INTO chat_service.conversations
                (id,user_low,user_high) VALUES (:id,:a,:b)"""),
                {"id": cid, "a": low, "b": high},
            )
            await session.execute(
                text("""INSERT INTO chat_service.conversation_participants
                (conversation_id,user_id) VALUES (:id,:a),(:id,:b)"""),
                {"id": cid, "a": low, "b": high},
            )
        return {"conversationId": str(cid)}

    async def summary(self, session, row, user_id, people):
        counterpart_id = other(row, user_id)
        person = people.get(counterpart_id)
        if person is None:
            # Unknown is not a tombstone. Fail closed instead of inventing an identity.
            raise unavailable()
        latest = (
            (
                await session.execute(
                    text("""SELECT * FROM chat_service.messages
            WHERE conversation_id=:cid ORDER BY sequence DESC LIMIT 1"""),
                    {"cid": row["id"]},
                )
            )
            .mappings()
            .first()
        )
        unread = (
            await session.execute(
                text("""SELECT count(*) FROM chat_service.messages
            WHERE conversation_id=:cid AND sequence>:seq AND sender_id<>:uid"""),
                {"cid": row["id"], "seq": row["last_read_sequence"], "uid": user_id},
            )
        ).scalar_one()
        is_blocked = await blocked(session, row["user_low"], row["user_high"])
        return {
            "conversationId": str(row["id"]),
            "counterpart": person,
            "latestMessage": message(latest) if latest else None,
            "unreadCount": unread,
            "lastReadSequence": row["last_read_sequence"],
            "lastSequence": row["last_sequence"],
            "messagingAvailable": not is_blocked and person["accountStatus"] == "ACTIVE",
            "blocked": is_blocked,
            "createdAt": row["created_at"].isoformat(),
        }

    async def conversations(self, user_id, query):
        async with self.db.transaction() as session:
            rows = (
                (
                    await session.execute(
                        text("""
                SELECT c.*,p.last_read_sequence FROM chat_service.conversations c
                JOIN chat_service.conversation_participants p ON p.conversation_id=c.id
                WHERE p.user_id=:uid AND (CAST(:cursor AS uuid) IS NULL OR c.id>:cursor)
                ORDER BY c.id LIMIT :limit
            """),
                        {"uid": user_id, "cursor": query.cursor, "limit": query.limit + 1},
                    )
                )
                .mappings()
                .all()
            )
            selected = rows[: query.limit]
            people = await self.identity.participants([other(r, user_id) for r in selected])
            items = [await self.summary(session, r, user_id, people) for r in selected]
            return {
                "items": items,
                "nextCursor": str(selected[-1]["id"]) if len(rows) > query.limit else None,
            }

    async def conversation(self, user_id, cid):
        async with self.db.transaction() as session:
            row = await member(session, cid, user_id)
            people = await self.identity.participants([other(row, user_id)])
            return await self.summary(session, row, user_id, people)

    async def history(self, user_id, cid, query):
        async with self.db.transaction() as session:
            row = await member(session, cid, user_id)
            boundary = row["last_sequence"]
            clause, direction = "", "DESC"
            params = {"cid": cid, "limit": query.limit + 1, "boundary": boundary}
            if query.beforeSequence is not None:
                clause, params["seq"] = "AND sequence<:seq", query.beforeSequence
            if query.afterSequence is not None:
                clause, params["seq"] = "AND sequence>:seq", query.afterSequence
                direction = "ASC"
            rows = (
                (
                    await session.execute(
                        text(f"""SELECT * FROM chat_service.messages
                WHERE conversation_id=:cid AND sequence<=:boundary {clause}
                ORDER BY sequence {direction} LIMIT :limit"""),
                        params,
                    )
                )
                .mappings()
                .all()
            )
            selected = rows[: query.limit]
            if direction == "DESC":
                selected = list(reversed(selected))
            return {
                "items": [message(r) for r in selected],
                "boundarySequence": boundary,
                "lastReadSequence": row["last_read_sequence"],
                "hasMore": len(rows) > query.limit,
            }
