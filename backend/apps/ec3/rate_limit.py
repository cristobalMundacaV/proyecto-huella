import math

from django.core.exceptions import ValidationError
from django.db import connection, transaction

from .models import RateBudget


class RateLimited(Exception):
    def __init__(self, seconds):
        self.retry_after = max(1, math.ceil(seconds))
        super().__init__("Presupuesto EC3 temporalmente agotado.")


class DatabaseRateLimiter:
    """Sliding 60-second token window; no per-process or cache-eviction bypass."""
    key = "carbono-zero-ec3-pilot"
    capacity = 100

    def _require_postgres(self):
        if connection.vendor != "postgresql":
            raise ValidationError("El rate limiter EC3 compartido requiere PostgreSQL.")

    def _now(self):
        # A shared server clock prevents clock skew across application nodes.
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXTRACT(EPOCH FROM clock_timestamp())")
            return float(cursor.fetchone()[0])

    def acquire(self, cost):
        self._require_postgres()
        if not isinstance(cost, (int, float)) or not math.isfinite(cost) or not 0 < cost <= self.capacity:
            raise ValidationError("Coste EC3 fuera del presupuesto de 100 tokens/min.")
        RateBudget.objects.get_or_create(key=self.key)
        with transaction.atomic():
            budget = RateBudget.objects.select_for_update().get(key=self.key)
            now = self._now()
            if budget.blocked_until > now:
                raise RateLimited(budget.blocked_until - now)
            events = [event for event in budget.events if event[0] > now - 60]
            used = sum(event[1] for event in events)
            if used + cost > self.capacity:
                for stamp, spent in events:
                    used -= spent
                    if used + cost <= self.capacity:
                        raise RateLimited(stamp + 60 - now)
            events.append([now, cost])
            budget.events = events
            budget.save(update_fields=["events"])

    def defer(self, seconds):
        self._require_postgres()
        RateBudget.objects.get_or_create(key=self.key)
        with transaction.atomic():
            budget = RateBudget.objects.select_for_update().get(key=self.key)
            budget.blocked_until = max(budget.blocked_until, self._now() + seconds)
            budget.save(update_fields=["blocked_until"])
