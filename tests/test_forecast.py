"""월말 지출 예측(forecast) 테스트. 담당: 기능 5(이정배)."""

import copy
import datetime as dt
import unittest

from helpers import NAMES, StoreCase
from moim.features import budget

KIM, LEE, PARK = NAMES


class TestForecast(StoreCase):
    def _add_expense(self, date, amount, deleted=False):
        self.store.data["expenses"].append({
            "id": self.store.new_id(),
            "date": date,
            "payer": KIM,
            "amount": amount,
            "members": [KIM, LEE, PARK],
            "category": "식비",
            "memo": "",
            "deleted": deleted,
        })

    def test_mid_month_projection(self):
        self._add_expense("2026-11-05", 40000)
        self._add_expense("2026-11-15", 60000)
        # 11월은 30일, 15일 경과 시 100,000원 -> 월말 예측 200,000원
        self.assertEqual(budget.forecast(self.store, "2026-11", "2026-11-15"), 200000)

    def test_half_up_rounding(self):
        # 11월 30일, 4일 경과 시 1,001원 -> (1001 * 30) / 4 = 7507.5 -> 7508
        self._add_expense("2026-11-04", 1001)
        self.assertEqual(budget.forecast(self.store, "2026-11", "2026-11-04"), 7508)

    def test_leap_year_and_common_february(self):
        self._add_expense("2024-02-01", 1000)
        self._add_expense("2026-02-01", 1000)
        self.assertEqual(budget.forecast(self.store, "2024-02", dt.date(2024, 2, 1)), 29000)
        self.assertEqual(budget.forecast(self.store, "2026-02", dt.date(2026, 2, 1)), 28000)

    def test_ignores_expenses_after_today_and_deleted(self):
        self._add_expense("2026-11-10", 30000)
        self._add_expense("2026-11-10", 50000, deleted=True)
        self._add_expense("2026-11-20", 90000)
        # 10일 경과 기준 30,000원 -> (30000 / 10) * 30 = 90,000원
        self.assertEqual(budget.forecast(self.store, "2026-11", "2026-11-10"), 90000)

    def test_before_start_and_at_or_after_end(self):
        self._add_expense("2026-11-10", 30000)
        self._add_expense("2026-11-25", 20000)
        self.assertEqual(budget.forecast(self.store, "2026-11", "2026-10-31"), 0)
        self.assertEqual(budget.forecast(self.store, "2026-11", "2026-11-30"), 50000)
        self.assertEqual(budget.forecast(self.store, "2026-11", "2026-12-10"), 50000)

    def test_invalid_month_or_today_raises(self):
        with self.assertRaises(ValueError):
            budget.forecast(self.store, "2026-13", "2026-11-10")
        with self.assertRaises(ValueError):
            budget.forecast(self.store, "2026-11", "2026-02-30")

    def test_does_not_mutate_store(self):
        self._add_expense("2026-11-10", 30000)
        before = copy.deepcopy(self.store.data)
        budget.forecast(self.store, "2026-11", "2026-11-10")
        self.assertEqual(self.store.data, before)


if __name__ == "__main__":
    unittest.main()