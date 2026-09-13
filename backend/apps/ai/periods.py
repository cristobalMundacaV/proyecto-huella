"""AI-INTELLIGENCE-02 — deterministic period resolution.

The model expresses relative time ("los últimos 3 meses") as an integer;
the exact calendar boundaries are always computed here, server-side, from
the real current date — never left to the LLM to compute or guess.
"""
from datetime import date as date_cls, timedelta


def _months_ago(today, months):
    """Same day-of-month `months` calendar months before `today` (clamped
    to the shorter month's last day, e.g. Mar 31 - 1 month = Feb 28/29).
    Pure stdlib — avoids an undeclared dateutil dependency."""
    month_index = today.month - 1 - months
    year = today.year + month_index // 12
    month = month_index % 12 + 1
    day = today.day
    while True:
        try:
            return date_cls(year, month, day)
        except ValueError:
            day -= 1  # walk back to the last valid day of that month


def resolve_period(*, date_from=None, date_to=None, relative_months=None, today=None):
    """Returns (start, end) as `date` objects, or (None, None) if nothing
    was specified (meaning: no date filter, all available history)."""
    today = today or date_cls.today()
    if date_from or date_to:
        start = _parse(date_from)
        end = _parse(date_to) or today
        return start, end
    if relative_months:
        months = max(1, int(relative_months))
        start = _months_ago(today, months) + timedelta(days=1)
        return start, today
    return None, None


def _parse(value):
    if not value:
        return None
    if isinstance(value, date_cls):
        return value
    try:
        return date_cls.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def resolve_comparison_periods(*, date_from=None, date_to=None, relative_months=None, today=None):
    """AI-INTELLIGENCE-03: a diagnostic always compares a current period
    against an immediately-preceding period of the SAME length — computed
    here, once, so every rule and every LLM sees identical boundaries for
    identical inputs. Defaults to "this calendar month vs last calendar
    month" when nothing is specified (matches "esta obra este mes")."""
    today = today or date_cls.today()
    if date_from or date_to or relative_months:
        current_start, current_end = resolve_period(
            date_from=date_from, date_to=date_to, relative_months=relative_months, today=today,
        )
        if current_start is None:
            current_start, current_end = today.replace(day=1), today
    else:
        current_start, current_end = today.replace(day=1), today
    span_days = (current_end - current_start).days + 1
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=span_days - 1)
    return current_start, current_end, previous_start, previous_end
