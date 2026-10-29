from uuid import uuid4

import httpx
import pytest

from app.admin.errors import ApiError
from app.admin.orders import OrderDirectory
from app.core.config import Settings

ORDER_ID = uuid4()


def directory(handler, base="http://order-service:8002"):
    settings = Settings(_env_file=None, order_service_base_url=base)
    return OrderDirectory(settings, httpx.AsyncClient(transport=httpx.MockTransport(handler)))


async def test_forwards_the_administrator_token_to_the_admin_detail_route():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        return httpx.Response(200, json={"orderId": str(ORDER_ID)})

    assert await directory(handler).exists(ORDER_ID, "abc") is True
    assert seen == {
        "url": f"http://order-service:8002/v1/admin/orders/{ORDER_ID}",
        "auth": "Bearer abc",
    }


async def test_unknown_errand_is_reported_as_missing():
    assert await directory(lambda request: httpx.Response(404)).exists(ORDER_ID, "abc") is False


@pytest.mark.parametrize("status", [401, 403])
async def test_order_authorization_failures_are_passed_on(status):
    with pytest.raises(ApiError) as error:
        await directory(lambda request: httpx.Response(status)).exists(ORDER_ID, "abc")
    assert error.value.status == status


@pytest.mark.parametrize(
    "response",
    [httpx.Response(500), httpx.Response(302, headers={"Location": "http://elsewhere/"})],
)
async def test_unusable_responses_fail_closed(response):
    with pytest.raises(ApiError) as error:
        await directory(lambda request: response).exists(ORDER_ID, "abc")
    assert (error.value.status, error.value.code) == (503, "ORDER_UNAVAILABLE")


@pytest.mark.parametrize(
    "body,expected",
    [
        (
            {"state": "DELIVERED", "requesterId": "me", "courierId": "them"},
            ("REQUESTER", "DELIVERED"),
        ),
        ({"state": "FAILED", "requesterId": "them", "courierId": "me"}, ("COURIER", "FAILED")),
        ({"state": "ACCEPTED", "requesterId": "them", "courierId": "other"}, None),
        ({"state": "OPEN", "orderId": "assessment view without participants"}, None),
    ],
)
async def test_participation_comes_from_orders_participant_view(body, expected):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json=body)

    assert await directory(handler).participation(ORDER_ID, "abc", "me") == expected
    assert seen["url"] == f"http://order-service:8002/v1/orders/{ORDER_ID}"


async def test_unknown_errand_has_no_participation():
    result = await directory(lambda request: httpx.Response(404)).participation(ORDER_ID, "a", "me")
    assert result is None


@pytest.mark.parametrize("base", ["http://order-service:8002", None])
async def test_unreachable_or_unconfigured_order_service_fails_closed(base):
    def refuse(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(ApiError) as error:
        await directory(refuse, base=base).exists(ORDER_ID, "abc")
    assert (error.value.status, error.value.code) == (503, "ORDER_UNAVAILABLE")
