"""기능 4: 특정 지출에서 특정 사람 빼기(exclude_member) 테스트."""

import copy
import unittest

from helpers import NAMES, StoreCase

from moim.common import queries
from moim.features import settle

KIM, LEE, PARK = NAMES


class ExcludeMember(StoreCase):
    def put(self, eid, date, payer, amount, members=None, weights=None, deleted=None):
        e = {"id": eid, "date": date, "payer": payer, "amount": amount,
             "members": list(members or NAMES), "category": None, "memo": "", "weights": weights}
        if deleted is not None:
            e["deleted"] = deleted
        self.store.data["expenses"].append(e)
        return e

    def test_removes_and_rest_share(self):
        self.put(1, "2026-11-12", KIM, 9000)
        e = settle.exclude_member(self.store, 1, PARK)
        self.assertEqual(e["members"], [KIM, LEE])
        self.assertEqual(queries.expense_shares(e), {KIM: 4500, LEE: 4500})
        self.assertEqual(sum(queries.member_shares(self.store, "2026-11-01", "2026-11-30").values()), 9000)

    def test_keeps_member_order_and_remainder(self):
        # 이서연(낸 사람)을 빼면 낸 사람이 참여자가 아니므로 나머지 1원은 참여자 목록 순서(박 먼저)로 간다(규약 2절)
        self.put(1, "2026-11-12", LEE, 10001, members=[PARK, LEE, KIM])
        e = settle.exclude_member(self.store, "1", LEE)
        self.assertEqual(e["members"], [PARK, KIM])
        self.assertEqual(queries.expense_shares(e), {PARK: 5001, KIM: 5000})

    def test_weights_drop_that_person(self):
        self.put(1, "2026-11-12", KIM, 10000, weights={KIM: 2, LEE: 1, PARK: 1})
        e = settle.exclude_member(self.store, 1, LEE)
        self.assertEqual(e["weights"], {KIM: 2, PARK: 1})
        self.assertEqual(queries.expense_shares(e), {KIM: 6667, PARK: 3333})

    def test_records_history(self):
        before = copy.deepcopy(self.put(1, "2026-11-12", KIM, 9000))
        e = settle.exclude_member(self.store, 1, PARK)
        entry = self.store.data["history"][-1]
        self.assertEqual((entry["action"], entry["eid"]), ("exclude", 1))
        self.assertEqual(entry["before"], before)
        self.assertEqual(entry["after"], e)
        e["memo"] = "나중에 바꿈"
        self.assertEqual(entry["after"]["memo"], "")   # 이력은 사본(규격 1-2)

    def test_rejects_and_keeps_data(self):
        self.put(1, "2026-11-12", KIM, 9000)
        self.put(2, "2026-11-12", KIM, 9000, members=[KIM])
        self.put(3, "2026-11-12", KIM, 9000, deleted=True)
        self.put(4, "2026-10-12", KIM, 9000)
        self.store.data["locks"].append({"start": "2026-10-01", "end": "2026-10-31"})
        snapshot = copy.deepcopy(self.store.data)
        for eid, name in ((1, "명부에없음"), (2, KIM), (3, PARK), (4, PARK), (99, PARK)):
            with self.subTest(eid=eid, name=name):
                with self.assertRaises(ValueError):
                    settle.exclude_member(self.store, eid, name)
        self.assertEqual(self.store.data, snapshot)


if __name__ == "__main__":
    unittest.main()
