import datetime
import json
import unittest

from helpers import StoreCase

from moim.common import money, queries
from moim.common.store import Store


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


class ExpenseShares(unittest.TestCase):
    M = ["가", "나", "다"]

    def expense(self, amount, payer="나", **kw):
        e = {"id": 1, "date": "2026-11-12", "payer": payer, "amount": amount,
             "members": list(self.M), "category": None, "memo": ""}
        e.update(kw)
        return e

    def test_no_weights_field_is_even(self):
        self.assertEqual(queries.expense_shares(self.expense(9000)), {"가": 3000, "나": 3000, "다": 3000})

    def test_null_weights_is_even(self):
        self.assertEqual(queries.expense_shares(self.expense(10000, weights=None)),
                         money.split(10000, self.M, "나"))

    def test_weights(self):
        e = self.expense(10001, weights={"가": 2, "나": 1, "다": 1})
        self.assertEqual(queries.expense_shares(e), {"가": 5000, "나": 2501, "다": 2500})

    def test_remainder_to_payer(self):
        self.assertEqual(queries.expense_shares(self.expense(10000, payer="다")), {"가": 3333, "나": 3333, "다": 3334})

    def test_members_order_and_total(self):
        e = self.expense(36001, weights={"가": 3, "나": 2, "다": 1})
        shares = queries.expense_shares(e)
        self.assertEqual(list(shares), self.M)
        self.assertEqual(sum(shares.values()), 36001)

    def test_deleted_not_checked(self):
        self.assertEqual(queries.expense_shares(self.expense(9000, deleted=True)), {"가": 3000, "나": 3000, "다": 3000})


class SettleDataItems(StoreCase):
    def test_new_store_has_items(self):
        self.assertEqual(self.store.data["transfers"], [])
        self.assertEqual(self.store.data["recurring"], [])

    def test_old_data_without_items(self):
        path = self.path("old.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"members": [], "expenses": [], "next_id": 1}, f)
        data = Store(path).load().data
        self.assertEqual(data["transfers"], [])
        self.assertEqual(data["recurring"], [])


if __name__ == "__main__":
    unittest.main()
