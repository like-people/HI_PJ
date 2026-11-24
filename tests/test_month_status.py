"""월 예산 상태(month_status) 테스트. 담당: 기능 5(이정배)."""

import copy
import datetime as dt
import unittest

from helpers import NAMES, StoreCase
from moim.features import budget

KIM, LEE, PARK = NAMES


class TestMonthStatus(StoreCase):
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

    def test_normal_under_budget(self):
        self._add_expense("2026-11-10", 30000)
        status = budget.month_status(self.store, self.cfg, "2026-11")
        self.assertEqual(status, {
            "budget": 100000,
            "spent": 30000,
            "remaining": 70000,
            "over": False,
            "warn": False,
        })

    def test_warn_threshold_and_exact_budget(self):
        self._add_expense("2026-11-10", 80000)
        below = budget.month_status(self.store, self.cfg, "2026-11")
        self.assertEqual((below["warn"], below["over"]), (False, False))

        self._add_expense("2026-11-11", 1)
        at_warn = budget.month_status(self.store, self.cfg, "2026-11")
        self.assertEqual(at_warn, {
            "budget": 100000,
            "spent": 80001,
            "remaining": 19999,
            "over": False,
            "warn": True,
        })

        self._add_expense("2026-11-12", 19999)
        exact = budget.month_status(self.store, self.cfg, "2026-11")
        self.assertEqual(exact, {
            "budget": 100000,
            "spent": 100000,
            "remaining": 0,
            "over": False,
            "warn": True,
        })

    def test_over_budget(self):
        self._add_expense("2026-11-10", 120000)
        status = budget.month_status(self.store, self.cfg, "2026-11")
        self.assertEqual(status, {
            "budget": 100000,
            "spent": 120000,
            "remaining": -20000,
            "over": True,
            "warn": True,
        })

    def test_today_filters_expenses(self):
        self._add_expense("2026-11-05", 25000)
        self._add_expense("2026-11-15", 40000)
        self._add_expense("2026-11-25", 50000)

        mid = budget.month_status(self.store, self.cfg, "2026-11", today="2026-11-15")
        self.assertEqual(mid["spent"], 65000)
        self.assertEqual(mid["remaining"], 35000)
        self.assertEqual((mid["over"], mid["warn"]), (False, False))

        before_month = budget.month_status(
            self.store, self.cfg, "2026-11", today=dt.date(2026, 10, 31)
        )
        self.assertEqual(before_month["spent"], 0)
        self.assertEqual(before_month["remaining"], 100000)

        after_month = budget.month_status(self.store, self.cfg, "2026-11", today="2026-12-10")
        self.assertEqual(after_month["spent"], 115000)
        self.assertEqual(after_month["over"], True)

    def test_excludes_deleted_and_other_months(self):
        self._add_expense("2026-10-31", 50000)
        self._add_expense("2026-11-10", 30000)
        self._add_expense("2026-11-12", 40000, deleted=True)
        self._add_expense("2026-12-01", 50000)

        status = budget.month_status(self.store, self.cfg, "2026-11")
        self.assertEqual(status["spent"], 30000)
        self.assertEqual(status["remaining"], 70000)

    def test_unset_monthly_budget(self):
        self.cfg["budget"]["monthly"] = None
        self._add_expense("2026-11-10", 30000)

        status = budget.month_status(self.store, self.cfg, "2026-11")
        self.assertEqual(status, {
            "budget": None,
            "spent": 30000,
            "remaining": None,
            "over": False,
            "warn": False,
        })

    def test_invalid_budget_or_warn_ratio_raises(self):
        for bad in (-1, True, "100000"):
            with self.subTest(monthly=bad):
                cfg = copy.deepcopy(self.cfg)
                cfg["budget"]["monthly"] = bad
                with self.assertRaises(ValueError):
                    budget.month_status(self.store, cfg, "2026-11")

        for bad_ratio in (-0.1, 1.5, True, "0.8"):
            with self.subTest(warn_ratio=bad_ratio):
                cfg = copy.deepcopy(self.cfg)
                cfg["warn_ratio"] = bad_ratio
                with self.assertRaises(ValueError):
                    budget.month_status(self.store, cfg, "2026-11")

    def test_does_not_mutate_store_or_cfg(self):
        self._add_expense("2026-11-10", 30000)
        before_data = copy.deepcopy(self.store.data)
        before_cfg = copy.deepcopy(self.cfg)
        budget.month_status(self.store, self.cfg, "2026-11", today="2026-11-15")
        self.assertEqual(self.store.data, before_data)
        self.assertEqual(self.cfg, before_cfg)


if __name__ == "__main__":
    unittest.main()