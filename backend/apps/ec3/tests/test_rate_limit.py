from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.db import connection, connections
from django.test import TransactionTestCase

from apps.ec3.models import RateBudget
from apps.ec3.rate_limit import DatabaseRateLimiter, RateLimited


class RateLimitTests(TransactionTestCase):
    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("Shared limiter guarantees require PostgreSQL")
        self.limiter = DatabaseRateLimiter()
        RateBudget.objects.all().delete()

    def _fixture_teardown(self):
        # These tests write ONLY this table. Legacy unmanaged FK tables make
        # Django's global flush unsuitable; preserve all other apps and migrations.
        RateBudget.objects.all().delete()

    def test_sliding_window_no_boundary_burst(self):
        with patch.object(DatabaseRateLimiter, "_now", return_value=1000):
            self.limiter.acquire(100)
        with patch.object(DatabaseRateLimiter, "_now", return_value=1059):
            with self.assertRaises(RateLimited):
                self.limiter.acquire(1)
        with patch.object(DatabaseRateLimiter, "_now", return_value=1060):
            self.limiter.acquire(100)

    def test_429_block_shared_across_instances(self):
        with patch.object(DatabaseRateLimiter, "_now", return_value=1000):
            self.limiter.defer(120)
        with patch.object(DatabaseRateLimiter, "_now", return_value=1060):
            with self.assertRaises(RateLimited) as error:
                DatabaseRateLimiter().acquire(1)
            self.assertEqual(error.exception.retry_after, 60)

    def test_concurrent_workers_cannot_double_spend(self):
        RateBudget.objects.create(key=self.limiter.key)
        def spend(_):
            try:
                DatabaseRateLimiter().acquire(100)
                return "accepted"
            except RateLimited:
                return "limited"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(spend, range(2))), ["accepted", "limited"])
