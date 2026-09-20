#!/usr/bin/env python3
"""Generate non-production User Service secrets without printing them.

Run from user-service after `npx supabase start`:
    py scripts/generate_dev_secrets.py

The script creates an ignored `.env` file and RSA key pair under
`secrets/development/`. It never sends values to stdout. Existing targets are
left unchanged unless `--force` is passed deliberately.
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = SERVICE_ROOT / ".env"
DEFAULT_KEY_DIRECTORY = SERVICE_ROOT / "secrets" / "development"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing .env file and development key pair",
    )
    return parser.parse_args()


def load_cryptography():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ModuleNotFoundError as error:
        message = (
            "The cryptography package is required to generate the RSA key pair. "
            "Create the User Service virtual environment and install project "
            "dependencies first."
        )
        raise SystemExit(message) from error
    return serialization, rsa


def local_database_url() -> str:
    """Read only DB_URL from the local CLI status; never echo CLI secrets."""

    result = subprocess.run(
        ["npx", "supabase", "status", "-o", "env"],
        cwd=SERVICE_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return ""

    for line in result.stdout.splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == "DB_URL":
            value = value.strip().strip('"').strip("'")
            if value.startswith("postgres://"):
                return "postgresql+asyncpg://" + value.removeprefix("postgres://")
            if value.startswith("postgresql://"):
                return "postgresql+asyncpg://" + value.removeprefix("postgresql://")
            return value
    return ""


def assert_writable(targets: list[Path], force: bool) -> None:
    existing = [target for target in targets if target.exists()]
    if existing and not force:
        joined = ", ".join(str(target.relative_to(SERVICE_ROOT)) for target in existing)
        raise SystemExit(
            f"Refusing to overwrite existing development secrets: {joined}. "
            "Move them aside or re-run with --force."
        )


def write_private_file(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    try:
        os.chmod(path, 0o600)
    except OSError:
        # Windows ACLs remain authoritative when POSIX modes are unavailable.
        pass


def write_environment_file(path: Path, database_url: str) -> None:
    values = {
        "ENVIRONMENT": "development",
        "DATABASE_URL": database_url,
        "JWT_PRIVATE_KEY_PATH": "secrets/development/jwt_private_key.pem",
        "JWT_PUBLIC_KEY_PATH": "secrets/development/jwt_public_key.pem",
        "JWT_ISSUER": "foc-user-service",
        "JWT_AUDIENCE": "foc-services",
        "JWT_ACCESS_TOKEN_TTL_SECONDS": "900",
        "JWT_REFRESH_TOKEN_TTL_SECONDS": "1209600",
        "OTP_HMAC_SECRET": secrets.token_urlsafe(32),
        "INTERNAL_SERVICE_SECRET": secrets.token_urlsafe(32),
        "SMTP_HOST": "127.0.0.1",
        "SMTP_PORT": "1025",
        "SMTP_FROM": "no-reply@foc.local",
        "RABBITMQ_URL": "amqp://guest:guest@127.0.0.1:5672/",
    }
    lines = ["# Generated for local development. Do not commit this file."]
    if not database_url:
        lines.append("# Start local Supabase first, then rerun with --force to fill DATABASE_URL.")
    lines.extend(f"{name}={value}" for name, value in values.items())
    write_private_file(path, ("\n".join(lines) + "\n").encode("utf-8"))


def main() -> None:
    arguments = parse_arguments()
    serialization, rsa = load_cryptography()
    private_path = DEFAULT_KEY_DIRECTORY / "jwt_private_key.pem"
    public_path = DEFAULT_KEY_DIRECTORY / "jwt_public_key.pem"
    assert_writable([DEFAULT_ENV_FILE, private_path, public_path], arguments.force)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    write_private_file(private_path, private_pem)
    write_private_file(public_path, public_pem)
    write_environment_file(DEFAULT_ENV_FILE, local_database_url())

    print("Created ignored development secrets in .env and secrets/development/.")
    print("No secret values were printed.")


if __name__ == "__main__":
    main()
