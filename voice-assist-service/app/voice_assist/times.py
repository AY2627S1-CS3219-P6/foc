"""Deterministic time resolution in Asia/Singapore (N3F2.1.3, N3F2.1.4).

The provider only reports what was said; this module decides what it means, so a vague or
unsupported phrase can never become an invented timestamp."""

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.voice_assist.schemas import DraftField, TimePhrase

SGT = ZoneInfo("Asia/Singapore")
_CLOCK = re.compile(r"([01]?\d|2[0-3]):([0-5]\d)")
MAX_RELATIVE_MINUTES = 7 * 24 * 60


def _ceil_minute(value: datetime) -> datetime:
    # The form keeps minutes only; rounding up keeps "in 1 minute" in the future.
    floored = value.replace(second=0, microsecond=0)
    return floored if floored == value else floored + timedelta(minutes=1)


def display(value: datetime, now: datetime) -> str:
    local, today = value.astimezone(SGT), now.astimezone(SGT).date()
    if local.date() == today:
        day = "Today"
    elif local.date() == today + timedelta(days=1):
        day = "Tomorrow"
    else:
        day = local.strftime("%a %d %b")
    clock = local.strftime("%I:%M %p").lstrip("0")
    return f"{day}, {clock} SGT"


def _filled(value: datetime, now: datetime) -> DraftField:
    utc = value.astimezone(UTC)
    return DraftField(
        value=utc.isoformat().replace("+00:00", "Z"), status="FILLED", display=display(utc, now)
    )


def resolve(phrase: TimePhrase | None, now: datetime, label: str) -> DraftField:
    """Resolve one spoken time against the draft-generation request time."""
    if phrase is None:
        return DraftField(status="MISSING", note=f"Enter the {label}.")
    unclear = DraftField(
        status="AMBIGUOUS", note=f"We could not tell the exact {label}. Enter it below."
    )
    if phrase.relative_minutes is not None:
        if phrase.day is not None or phrase.clock is not None:
            return unclear
        if not 0 < phrase.relative_minutes <= MAX_RELATIVE_MINUTES:
            return unclear
        return _filled(_ceil_minute(now + timedelta(minutes=phrase.relative_minutes)), now)
    if phrase.clock is None:
        # "tomorrow" alone, or an unsupported expression such as "after lunch".
        return unclear
    match = _CLOCK.fullmatch(phrase.clock.strip())
    if not match:
        return unclear
    local_now = now.astimezone(SGT)
    date = local_now.date() + timedelta(days=1 if phrase.day == "TOMORROW" else 0)
    value = datetime(date.year, date.month, date.day, int(match[1]), int(match[2]), tzinfo=SGT)
    if value > now:
        return _filled(value, now)
    if phrase.day is None:
        # A clock time without a day means today only while it is still ahead.
        return DraftField(
            status="AMBIGUOUS",
            note=f"That time has passed today. Enter the {label} with the right day.",
        )
    return DraftField(status="CONFLICT", note=f"That {label} has already passed.")
