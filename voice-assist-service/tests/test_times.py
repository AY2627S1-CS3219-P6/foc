"""N3F2.1.3 and N3F2.1.4: spoken times resolve in Asia/Singapore against the request time."""

from datetime import UTC, datetime

import pytest

from app.voice_assist.schemas import TimePhrase
from app.voice_assist.times import resolve

# 30 Oct 2026, 13:20:30 in Singapore.
NOW = datetime(2026, 10, 30, 5, 20, 30, tzinfo=UTC)


def phrase(raw="x", day=None, clock=None, minutes=None):
    return TimePhrase(raw=raw, day=day, clock=clock, relative_minutes=minutes)


@pytest.mark.parametrize(
    ("spoken", "expected", "display"),
    [
        (phrase(day="TODAY", clock="15:00"), "2026-10-30T07:00:00Z", "Today, 3:00 PM SGT"),
        (phrase(day="TOMORROW", clock="09:30"), "2026-10-31T01:30:00Z", "Tomorrow, 9:30 AM SGT"),
        (phrase(clock="15:00"), "2026-10-30T07:00:00Z", "Today, 3:00 PM SGT"),
        # Rounded up to the next minute so the form keeps it in the future.
        (phrase(minutes=20), "2026-10-30T05:41:00Z", "Today, 1:41 PM SGT"),
        (phrase(minutes=60), "2026-10-30T06:21:00Z", "Today, 2:21 PM SGT"),
        (phrase(minutes=30), "2026-10-30T05:51:00Z", "Today, 1:51 PM SGT"),
    ],
)
def test_supported_expressions_resolve(spoken, expected, display):
    field = resolve(spoken, NOW, "latest delivery time")
    assert (field.status, field.value, field.display) == ("FILLED", expected, display)


def test_minutes_cross_midnight_in_singapore_not_utc():
    late = datetime(2026, 10, 30, 15, 50, tzinfo=UTC)  # 23:50 SGT
    field = resolve(phrase(minutes=20), late, "latest delivery time")
    assert field.value == "2026-10-30T16:10:00Z"
    assert field.display == "Tomorrow, 12:10 AM SGT"


def test_tomorrow_uses_the_singapore_date():
    # 00:30 SGT on 31 Oct is still 30 Oct in UTC.
    early = datetime(2026, 10, 30, 16, 30, tzinfo=UTC)
    field = resolve(phrase(day="TOMORROW", clock="08:00"), early, "latest delivery time")
    assert field.value == "2026-11-01T00:00:00Z"


def test_missing_phrase_is_missing():
    assert resolve(None, NOW, "latest acceptance time").status == "MISSING"


@pytest.mark.parametrize(
    "spoken",
    [
        phrase(day="TOMORROW"),  # a day without a time
        phrase(raw="after lunch"),  # unsupported expression
        phrase(clock="3pm"),  # not HH:MM
        phrase(clock="25:00"),
        phrase(minutes=0),
        phrase(minutes=-5),
        phrase(day="TODAY", minutes=10),  # mixed forms
        phrase(clock="10:00"),  # clock-only time already passed today
    ],
)
def test_unclear_expressions_are_left_for_manual_entry(spoken):
    field = resolve(spoken, NOW, "latest delivery time")
    assert field.status == "AMBIGUOUS"
    assert field.value is None


def test_past_time_with_a_day_is_a_conflict():
    field = resolve(phrase(day="TODAY", clock="09:00"), NOW, "latest acceptance time")
    assert (field.status, field.value) == ("CONFLICT", None)
