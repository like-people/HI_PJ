"""기능 4: 정산 확정(lock_period) 테스트."""

import copy
import datetime
import unittest

from helpers import NAMES, StoreCase

from moim.common import queries
from moim.features import settle

KIM, LEE, PARK = NAMES
NOV = {"start": "2026-11-01", "end": "2026-11-30"}


class LockPeriod(StoreCase):
    def put(self, eid, date, payer, amount, members):
        self.store.data["expenses"].append({"id": eid, "date": date, "payer": payer, "amount": amount,
                                            "members": members, "category": None, "memo": ""})

    def test_locks_period(self):
        self.put(1, "2026-11-12", KIM, 10000, NAMES)
        self.assertEqual(settle.lock_period(self.store, "2026-11-01", "2026-11-30"), NOV)
        self.assertEqual(self.store.data["locks"], [NOV])

    def test_locked_dates_and_edges(self):
        # 규약 3절: 시작일·끝일 포함. is_locked 와 함께 쓰인다
        settle.lock_period(self.store, "2026-11-01", "2026-11-30")
        for day, locked in (("2026-10-31", False), ("2026-11-01", True),
                            ("2026-11-30", True), ("2026-12-01", False)):
            with self.subTest(day=day):
                self.assertEqual(queries.is_locked(self.store, day), locked)

    def test_normalizes_dates(self):
        lock = settle.lock_period(self.store, datetime.date(2026, 11, 1), datetime.date(2026, 11, 30))
        self.assertEqual(lock, NOV)

    def test_empty_period_can_be_locked(self):
        self.assertEqual(settle.lock_period(self.store, "2026-11-01", "2026-11-30"), NOV)

    def test_same_period_is_not_added_twice(self):
        settle.lock_period(self.store, "2026-11-01", "2026-11-30")
        settle.lock_period(self.store, "2026-11-01", "2026-11-30")
        self.assertEqual(self.store.data["locks"], [NOV])

    def test_overlapping_periods_are_kept_separately(self):
        settle.lock_period(self.store, "2026-11-01", "2026-11-30")
        settle.lock_period(self.store, "2026-11-15", "2026-12-15")
        self.assertEqual(self.store.data["locks"], [NOV, {"start": "2026-11-15", "end": "2026-12-15"}])

    def test_rejects_when_balance_sum_is_not_zero(self):
        # 명부에 없는 사람이 낸 지출은 잔액 표에 들어가지 않아 잔액 합이 0이 아니게 된다
        self.put(1, "2026-11-12", "명부에없음", 9000, NAMES)
        before = copy.deepcopy(self.store.data)
        with self.assertRaisesRegex(ValueError, "잔액 합"):
            settle.lock_period(self.store, "2026-11-01", "2026-11-30")
        self.assertEqual(self.store.data, before)

    def test_rejects_invalid_period(self):
        for start, end, reason in (("2026-11-30", "2026-11-01", "늦습니다"),
                                   ("2026-02-30", "2026-03-01", "날짜")):
            with self.subTest(start=start, end=end), self.assertRaisesRegex(ValueError, reason):
                settle.lock_period(self.store, start, end)
        self.assertEqual(self.store.data["locks"], [])


if __name__ == "__main__":
    unittest.main()
