import datetime
import unittest

from helpers import StoreCase

from moim.common import money, queries


class IsLocked(StoreCase):
    NOV = {"start": "2026-11-01", "end": "2026-11-30"}

    def test_no_locks(self):
        self.assertFalse(queries.is_locked(self.store, "2026-11-15"))

    def test_inside_and_edges(self):
        self.store.data["locks"].append(self.NOV)
        self.assertTrue(queries.is_locked(self.store, "2026-11-01"))
        self.assertTrue(queries.is_locked(self.store, "2026-11-15"))
        self.assertTrue(queries.is_locked(self.store, "2026-11-30"))

    def test_outside(self):
        self.store.data["locks"].append(self.NOV)
        self.assertFalse(queries.is_locked(self.store, "2026-10-31"))
        self.assertFalse(queries.is_locked(self.store, "2026-12-01"))

    def test_date_object(self):
        self.store.data["locks"].append(self.NOV)
        self.assertTrue(queries.is_locked(self.store, datetime.date(2026, 11, 15)))

    def test_old_data_without_locks(self):
        del self.store.data["locks"]
        self.assertFalse(queries.is_locked(self.store, "2026-11-15"))


class SplitWeights(unittest.TestCase):
    M = ["가", "나", "다"]
    W = {"가": 2, "나": 1, "다": 1}

    def test_exact(self):
        self.assertEqual(money.split(10000, self.M, "가", self.W), {"가": 5000, "나": 2500, "다": 2500})

    def test_remainder_payer_first(self):
        self.assertEqual(money.split(10001, self.M, "나", self.W), {"가": 5000, "나": 2501, "다": 2500})

    def test_remainder_payer_not_member(self):
        self.assertEqual(money.split(10001, self.M, "라", self.W), {"가": 5001, "나": 2500, "다": 2500})

    def test_small_amount(self):
        self.assertEqual(money.split(101, self.M, "나", self.W), {"가": 50, "나": 26, "다": 25})

    def test_all_ones_same_as_even(self):
        self.assertEqual(money.split(10000, self.M, "나", {"가": 1, "나": 1, "다": 1}),
                         money.split(10000, self.M, "나"))

    def test_total_kept(self):
        for amount in (1, 99, 101, 10001, 36000):
            self.assertEqual(sum(money.split(amount, self.M, "나", self.W).values()), amount)


if __name__ == "__main__":
    unittest.main()
