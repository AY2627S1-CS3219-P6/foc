"""Explicit live local smoke: real User/Supplier + isolated Order + simulated Credit.

Creates two temporary User accounts, self-deletes them in finally; normal audit
records and the isolated demo errands remain. Never prints tokens/passwords/OTPs.
"""

import argparse
import json
import re
import secrets
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx

DEMO = Path(__file__).resolve().parent


def checked(response, status):
    if response.status_code != status:
        raise RuntimeError(f"Expected HTTP {status}, got {response.status_code}")
    return response.json() if status != 204 else None


def account(client):
    marker = uuid4().hex[:12]
    email, password = f"order-demo-{marker}@u.nus.edu", "DemoAa1!" + secrets.token_hex(16)
    checked(
        client.post(
            "/v1/auth/registrations",
            json={
                "username": f"Demo{marker}",
                "email": email,
                "password": password,
            },
        ),
        202,
    )
    for _ in range(30):
        messages = client.get("http://127.0.0.1:8025/api/v1/messages").json()["messages"]
        message = next((m for m in messages if any(r["Address"] == email for r in m["To"])), None)
        if message:
            break
        time.sleep(0.5)
    else:
        raise RuntimeError("Test verification email not received")
    body = client.get(f"http://127.0.0.1:8025/api/v1/message/{message['ID']}").json()
    otp = re.search(r"\b\d{6}\b", body["Text"])
    checked(
        client.post(
            "/v1/auth/email-verifications",
            json={
                "email": email,
                "otp": otp.group(),
            },
        ),
        201,
    )
    session = checked(
        client.post(
            "/v1/auth/sessions",
            json={
                "email": email,
                "password": password,
            },
        ),
        200,
    )
    headers = {"Authorization": f"Bearer {session['accessToken']}"}
    return password, headers


def simulated_states():
    output = subprocess.check_output(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "credit-simulator",
            "python",
            "credit_stub.py",
        ],
        cwd=DEMO,
        text=True,
    )
    return {
        value["orderId"]: value["state"]
        for line in output.splitlines()
        if line.startswith("{")
        for value in [json.loads(line)]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-test-accounts", action="store_true", required=True)
    parser.parse_args()
    accounts = []
    with httpx.Client(base_url="http://127.0.0.1:3001", timeout=20) as client:
        try:
            accounts.append(account(client))
            accounts.append(account(client))
            requester, courier = accounts[0][1], accounts[1][1]
            supplier = checked(client.get("/api/v1/suppliers", headers=requester), 200)["items"][0]

            def create(seconds=300):
                now = datetime.now(UTC)
                payload = {
                    "supplierId": supplier["id"],
                    "itemDescription": "Local demo smoke",
                    "deliveryLocation": "COM3 demo collection",
                    "reward": 5,
                    "acceptanceDeadline": (now + timedelta(seconds=seconds)).isoformat(),
                    "deliveryDeadline": (now + timedelta(minutes=30)).isoformat(),
                }
                headers = {**requester, "Idempotency-Key": uuid4().hex}
                result = checked(client.post("/v1/orders", headers=headers, json=payload), 201)
                repeated = checked(client.post("/v1/orders", headers=headers, json=payload), 200)
                assert result["orderId"] == repeated["orderId"]
                assert result["state"] == "OPEN"
                return result["orderId"]

            accepted = create()
            path = f"/v1/orders/{accepted}"
            checked(client.post(path + "/accept", headers=requester), 403)
            result = checked(client.post(path + "/accept", headers=courier), 200)
            assert result["state"] == "ACCEPTED"
            checked(client.post(path + "/accept", headers=courier), 200)
            checked(client.post(path + "/cancel", headers=requester), 409)
            assert checked(client.get(path + "/history", headers=courier), 200)["total"] == 2
            print("PASS real identity/supplier -> simulated reservation -> OPEN -> ACCEPTED/retry")
            cancelled = create()
            path = f"/v1/orders/{cancelled}"
            checked(client.post(path + "/cancel", headers=courier), 404)
            result = checked(client.post(path + "/cancel", headers=requester), 200)
            assert result["state"] == "CANCELLED"
            checked(client.post(path + "/cancel", headers=requester), 200)
            expired = create(seconds=8)
            for _ in range(30):
                states = simulated_states()
                if states.get(cancelled) == states.get(expired) == "RELEASED":
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Simulated releases not observed")
            result = checked(client.get(f"/v1/orders/{expired}", headers=requester), 200)
            assert result["state"] == "EXPIRED"
            assert states[accepted] == "RESERVED"
            print("PASS cancellation + automatic expiry -> real broker -> simulated release")
            failed_ids = []
            for picked_up, reporter in ((False, requester), (True, courier)):
                failed_id = create()
                failed_ids.append(failed_id)
                failure_path = f"/v1/orders/{failed_id}"
                checked(client.post(failure_path + "/accept", headers=courier), 200)
                if picked_up:
                    checked(client.post(failure_path + "/pickup", headers=courier), 200)
                report = {"reason": "ITEM_DAMAGED", "details": "Local smoke incident"}
                result = checked(
                    client.post(failure_path + "/fail", headers=reporter, json=report), 200
                )
                assert result["state"] == "FAILED" and result["failureReason"] == report["reason"]
                checked(client.post(failure_path + "/fail", headers=reporter, json=report), 200)
                checked(client.post(failure_path + "/deliver", headers=courier), 409)
                entries = checked(client.get(failure_path + "/history", headers=reporter), 200)
                assert entries["total"] == (4 if picked_up else 3)
            for _ in range(30):
                states = simulated_states()
                if all(states.get(order_id) == "RELEASED" for order_id in failed_ids):
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Simulated failure releases not observed")
            print("PASS unilateral requester/courier failure -> real broker -> simulated release")
            path = f"/v1/orders/{accepted}"
            checked(client.post(path + "/pickup", headers=requester), 403)
            assert (
                checked(client.post(path + "/pickup", headers=courier), 200)["state"] == "PICKED_UP"
            )
            assert (
                checked(client.post(path + "/deliver", headers=courier), 200)["state"]
                == "DELIVERED"
            )
            checked(client.post(path + "/complete", headers=courier), 403)
            # Simulate unavailable consumption, not just an HTTP failure.
            subprocess.run(
                ["docker", "compose", "stop", "credit-simulator"],
                cwd=DEMO,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            try:
                result = checked(client.post(path + "/complete", headers=requester), 200)
                assert result["state"] == "COMPLETED"
                checked(client.post(path + "/complete", headers=requester), 200)
                assert checked(client.get(path + "/history", headers=requester), 200)["total"] == 5
            finally:
                subprocess.run(
                    ["docker", "compose", "start", "credit-simulator"],
                    cwd=DEMO,
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
            for _ in range(30):
                states = simulated_states()
                if states.get(accepted) == "TRANSFERRED":
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Simulated transfer not observed")
            print("PASS pickup/delivery/completion, consumer outage, eventual simulated transfer")
            subprocess.run(
                ["docker", "compose", "restart", "credit-simulator"],
                cwd=DEMO,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            assert simulated_states() == states
            print("PASS simulator restart retains reservations and release state")
        finally:
            for password, headers in accounts:
                checked(
                    client.request(
                        "DELETE",
                        "/v1/users/me",
                        headers=headers,
                        json={
                            "currentPassword": password,
                            "acknowledgeDeletion": True,
                        },
                    ),
                    204,
                )
            print("Temporary accounts self-deleted; normal audit/demo evidence retained.")


if __name__ == "__main__":
    main()
