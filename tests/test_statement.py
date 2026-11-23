"""기능 4: 정산 내역서(statement) 테스트."""

import unittest

from helpers import NAMES, StoreCase

from moim.common import queries
from moim.features import settle

KIM, LEE, PARK = NAMES
S, E = "2026-11-01", "2026-11-30"


class Statement(StoreCase):
    def put(self, eid, date, payer, amount, members=None, memo="", weights=None, deleted=None):
        e = {"id": eid, "date": date, "payer": payer, "amount": amount,
             "members": list(members or NAMES), "category": None, "memo": memo, "weights": weights}
        if deleted is not None:
            e["deleted"] = deleted
        self.store.data["expenses"].append(e)

    def test_rows_and_shares(self):
        # 10,000원을 셋이 나누고 이서연이 냄 → 이 3,334(낸 사람 먼저 1원), 김·박 3,333 (규약 2절)
        self.put(1, "2026-11-12", LEE, 10000, memo="회식")
        self.assertEqual(settle.statement(self.store, S, E, KIM), [("2026-11-12", 1, "회식", 10000, 3333)])
        self.assertEqual(settle.statement(self.store, S, E, LEE), [("2026-11-12", 1, "회식", 10000, 3334)])

    def test_weights(self):
        self.put(1, "2026-11-12", KIM, 10000, weights={KIM: 2, LEE: 1, PARK: 1})
        self.assertEqual(settle.statement(self.store, S, E, KIM)[0][4], 5000)
        self.assertEqual(settle.statement(self.store, S, E, PARK)[0][4], 2500)

    def test_only_member_expenses_in_date_then_id_order(self):
        self.put(3, "2026-11-20", KIM, 3000)
        self.put(1, "2026-11-20", KIM, 3000)
        self.put(2, "2026-11-05", PARK, 2000, members=[KIM, LEE])   # 박지훈이 냈지만 참여자가 아님
        self.assertEqual([r[1] for r in settle.statement(self.store, S, E, KIM)], [2, 1, 3])
        self.assertEqual([r[1] for r in settle.statement(self.store, S, E, PARK)], [1, 3])

    def test_period_edges_and_deleted(self):
        self.put(1, "2026-10-31", KIM, 3000)
        self.put(2, "2026-11-01", KIM, 3000)
        self.put(3, "2026-11-30", KIM, 3000)
        self.put(4, "2026-12-01", KIM, 3000)
        self.put(5, "2026-11-15", KIM, 3000, deleted=True)
        self.assertEqual([r[1] for r in settle.statement(self.store, S, E, LEE)], [2, 3])

    def test_sum_equals_member_shares(self):
        self.put(1, "2026-11-03", KIM, 10000)
        self.put(2, "2026-11-10", LEE, 101, weights={KIM: 2, LEE: 1, PARK: 1})
        self.put(3, "2026-11-25", PARK, 7777, members=[LEE, PARK])
        shares = queries.member_shares(self.store, S, E)
        for name in NAMES:
            with self.subTest(name=name):
                self.assertEqual(sum(r[4] for r in settle.statement(self.store, S, E, name)), shares[name])

    def test_no_expense_is_empty(self):
        self.assertEqual(settle.statement(self.store, S, E, KIM), [])

    def test_unknown_person(self):
        with self.assertRaises(ValueError):
            settle.statement(self.store, S, E, "명부에없음")


if __name__ == "__main__":
    unittest.main()
