from uuid import uuid4

import httpx
import pytest

from app.config import Settings
from app.errors import ApiError
from app.identity import IdentityClient


async def test_signed_and_current_session(identity, directory):
    uid = directory.user()
    token = directory.token(uid)
    assert (await identity.authenticate(token)).user_id == uid
    directory.revoked.add(token)
    with pytest.raises(ApiError, match="") as caught:
        await identity.authenticate(token)
    assert caught.value.status == 401
    for changes in ({"exp": 1}, {"iss": "bad"}, {"aud": "bad"}, {"roleVersion": True}):
        with pytest.raises(ApiError):
            await identity.authenticate(directory.token(uid, **changes))
    directory.people[uid]["accountStatus"] = "DELETED"
    with pytest.raises(ApiError):
        await identity.authenticate(directory.token(uid))


async def test_batch_and_search_contract(identity, directory):
    ids = [directory.user(username=f"u{i}") for i in range(101)]
    missing = uuid4()
    directory.people[ids[0]].update(accountStatus="DELETED", displayName="Former", username="old")
    people = await identity.participants([*ids, missing])
    assert people[ids[0]]["displayName"] == "Deleted User"
    assert people[ids[0]]["username"] is None and missing not in people
    requests = [r for r in directory.calls if r.url.path.endswith("participants")]
    assert len(requests) == 2
    assert all("Authorization" not in r.headers for r in requests)
    caller = await identity.authenticate(directory.token(ids[1]))
    assert (await identity.search(caller, {"username": "lex", "cursor": "opaque"}))[
        "nextCursor"
    ] == "next-page"
    assert directory.calls[-1].headers["Authorization"] == f"Bearer {caller.token}"


@pytest.mark.parametrize(
    "status,data",
    [
        (503, {}),
        (200, {"items": [], "missingUserIds": []}),
        (200, {"items": [{"email": "private"}]}),
    ],
)
async def test_dependency_failure_is_closed(status, data):
    client = IdentityClient(
        Settings(_env_file=None, chat_service_shared_secret="test"),
        httpx.MockTransport(lambda r: httpx.Response(status, json=data)),
    )
    try:
        with pytest.raises(ApiError):
            await client.participants([uuid4()])
    finally:
        await client.close()
