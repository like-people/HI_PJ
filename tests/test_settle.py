import datetime
import json
import unittest

from helpers import NAMES, StoreCase

from moim.common import money, queries
from moim.common.store import Store
from moim.features import settle


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


class BalanceSum(unittest.TestCase):
    @staticmethod
    def row(paid, owed, sent=0, received=0):
        """balances 한 사람 칸. balance = paid - owed + sent - received (규격 4-3)."""
        return {"paid": paid, "owed": owed, "sent": sent, "received": received,
                "balance": paid - owed + sent - received}

    def test_zero_when_settled(self):
        # 6000원을 세 사람이 나누고 가가 냄: 가 +4000, 나 -2000, 다 -2000
        rows = {"가": self.row(6000, 2000), "나": self.row(0, 2000), "다": self.row(0, 2000)}
        self.assertEqual(settle.balance_sum(rows), 0)

    def test_zero_with_transfer(self):
        # 나가 가에게 2000원을 보낸 뒤에도 합은 0
        rows = {"가": self.row(6000, 2000, received=2000), "나": self.row(0, 2000, sent=2000),
                "다": self.row(0, 2000)}
        self.assertEqual(settle.balance_sum(rows), 0)

    def test_not_zero(self):
        # 합이 0이 아니면 그 값을 그대로 돌려준다(정산 확정 거부 판단에 쓰임)
        rows = {"가": self.row(4000, 0), "나": self.row(0, 1000)}
        self.assertEqual(settle.balance_sum(rows), 3000)

    def test_empty(self):
        self.assertEqual(settle.balance_sum({}), 0)


class MemberShares(StoreCase):
    S, E = "2026-11-01", "2026-11-30"

    def put(self, eid, date, payer, amount, members, weights=None, deleted=None):
        """기능 1(add_expense) 없이도 돌도록 지출 dict 를 자료에 직접 넣는다."""
        e = {"id": eid, "date": date, "payer": payer, "amount": amount,
             "members": list(members), "weights": weights, "category": None, "memo": ""}
        if deleted is not None:
            e["deleted"] = deleted
        self.store.data["expenses"].append(e)

    def shares(self, start=S, end=E):
        return queries.member_shares(self.store, start, end)

    def test_equal_split_remainder(self):
        # 10,000원을 셋이 나누고 이서연이 냄 → 나머지 1원은 낸 사람(규약 2절)
        kim, lee, park = NAMES
        self.put(1, "2026-11-10", lee, 10000, NAMES)
        self.assertEqual(self.shares(), {kim: 3333, lee: 3334, park: 3333})

    def test_weights(self):
        # 10,001원, 2:1:1, 이서연이 냄 → 김 5,000 · 이 2,501 · 박 2,500(규격 0-3 예)
        kim, lee, park = NAMES
        self.put(1, "2026-11-10", lee, 10001, NAMES, weights={kim: 2, lee: 1, park: 1})
        self.assertEqual(self.shares(), {kim: 5000, lee: 2501, park: 2500})

    def test_sums_over_expenses(self):
        kim, lee, park = NAMES
        self.put(1, "2026-11-10", lee, 9000, NAMES)
        self.put(2, "2026-11-11", kim, 4000, [kim, park])
        self.assertEqual(self.shares(), {kim: 5000, lee: 3000, park: 5000})

    def test_only_people_with_share(self):
        kim, lee, park = NAMES
        self.put(1, "2026-11-10", kim, 4000, [kim, park])
        self.assertNotIn(lee, self.shares())

    def test_zero_share_excluded(self):
        # 1원을 셋이 나누면 1원을 맡은 사람만 남는다(규격 4-1 "부담이 있는 사람만")
        kim, lee, park = NAMES
        self.put(1, "2026-11-10", kim, 1, NAMES)
        self.assertEqual(self.shares(), {kim: 1})

    def test_member_order(self):
        # 지출에 나온 순서(박 → 김)와 상관없이 명부 순서(김 → 박)
        kim, lee, park = NAMES
        self.put(1, "2026-11-10", park, 2000, [park, kim])
        self.assertEqual(list(self.shares()), [kim, park])

    def test_skips_deleted(self):
        kim, lee, park = NAMES
        self.put(1, "2026-11-10", kim, 3000, NAMES, deleted=True)
        self.put(2, "2026-11-11", kim, 3000, NAMES)
        self.assertEqual(self.shares(), {kim: 1000, lee: 1000, park: 1000})

    def test_period_includes_start_and_end(self):
        kim = NAMES[0]
        self.put(1, "2026-10-31", kim, 1, [kim])
        self.put(2, "2026-11-01", kim, 10, [kim])
        self.put(3, "2026-11-30", kim, 100, [kim])
        self.put(4, "2026-12-01", kim, 1000, [kim])
        self.assertEqual(self.shares(), {kim: 110})

    def test_total_equals_expense_total(self):
        # 규격 4-1: 부담액 합계 = 기간 지출 합계(통합 시나리오 6-2 4번)
        kim, lee, park = NAMES
        self.put(1, "2026-11-10", lee, 10000, NAMES)
        self.put(2, "2026-11-11", kim, 10001, NAMES, weights={kim: 2, lee: 1, park: 1})
        self.put(3, "2026-11-12", park, 7, [kim, park])
        self.assertEqual(sum(self.shares().values()), 10000 + 10001 + 7)

    def test_empty(self):
        self.assertEqual(self.shares(), {})


if __name__ == "__main__":
    unittest.main()
