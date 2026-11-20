"""기능 6: 기간 지출 합계 테스트"""

import unittest

from helpers import StoreCase
from moim.common.queries import period_total


class PeriodTotalTests(StoreCase):
    def add_expense(self, eid, date, amount, deleted=False):
        self.store.data["expenses"].append({
            "id": eid,
            "date": date,
            "amount": amount,
            "deleted": deleted,
        })

    def test_sum_in_period(self):
        self.add_expense(1, "2026-11-01", 1000)
        self.add_expense(2, "2026-11-15", 2000)
        self.add_expense(3, "2026-11-30", 3000)

        self.assertEqual(
            period_total(self.store, "2026-11-01", "2026-11-30"),
            6000,
        )

    def test_excludes_expenses_outside_period(self):
        self.add_expense(1, "2026-10-31", 1000)
        self.add_expense(2, "2026-11-01", 2000)
        self.add_expense(3, "2026-12-01", 3000)

        self.assertEqual(
            period_total(self.store, "2026-11-01", "2026-11-30"),
            2000,
        )

    def test_excludes_deleted_expenses(self):
        self.add_expense(1, "2026-11-10", 1000)
        self.add_expense(2, "2026-11-11", 2000, deleted=True)

        self.assertEqual(
            period_total(self.store, "2026-11-01", "2026-11-30"),
            1000,
        )

    def test_empty_period_returns_zero(self):
        self.assertEqual(
            period_total(self.store, "2026-11-01", "2026-11-30"),
            0,
        )


if __name__ == "__main__":
    unittest.main()
