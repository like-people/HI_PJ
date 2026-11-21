"""예산 대비 실제 표 자료(budget_table) 테스트. 담당: 기능 5(이정배)."""

import copy
import unittest

from helpers import NAMES, StoreCase
from moim.features import budget

KIM, LEE, PARK = NAMES


class TestBudgetTable(StoreCase):
    def _add_expense(self, date, amount, category="식비", deleted=False):
        self.store.data["expenses"].append({
            "id": self.store.new_id(),
            "date": date,
            "payer": KIM,
            "amount": amount,
            "members": [KIM, LEE, PARK],
            "category": category,
            "memo": "",
            "deleted": deleted,
        })

    def test_budgeted_categories_and_total_row(self):
        self.cfg["budget"]["monthly"] = 100000
        self.cfg["budget"]["by_category"] = {
            "식비": 60000,
            "장소": 30000,
            "교통": 10000,
        }
        self._add_expense("2026-11-05", 40000, category="식비")
        self._add_expense("2026-11-10", 35000, category="장소")

        rows = budget.budget_table(self.store, self.cfg, "2026-11")
        self.assertEqual(rows, [
            ("식비", 60000, 40000, 20000),
            ("장소", 30000, 35000, -5000),
            ("교통", 10000, 0, 10000),
            ("전체", 100000, 75000, 25000),
        ])

    def test_includes_unbudgeted_spending_categories(self):
        self.cfg["budget"]["monthly"] = 100000
        self.cfg["budget"]["by_category"] = {"식비": 50000}
        self._add_expense("2026-11-05", 20000, category="식비")
        self._add_expense("2026-11-10", 15000, category="간식")
        self._add_expense("2026-11-12", 5000, category=None)

        rows = budget.budget_table(self.store, self.cfg, "2026-11")
        self.assertEqual(rows, [
            ("식비", 50000, 20000, 30000),
            ("간식", 0, 15000, -15000),
            ("미분류", 0, 5000, -5000),
            ("전체", 100000, 40000, 60000),
        ])
        self.assertEqual(sum(r[2] for r in rows[:-1]), rows[-1][2])

    def test_excludes_deleted_and_other_months(self):
        self.cfg["budget"]["monthly"] = 100000
        self.cfg["budget"]["by_category"] = {"식비": 50000}
        self._add_expense("2026-10-31", 10000, category="식비")
        self._add_expense("2026-11-10", 20000, category="식비")
        self._add_expense("2026-11-12", 30000, category="식비", deleted=True)
        self._add_expense("2026-12-01", 10000, category="식비")

        rows = budget.budget_table(self.store, self.cfg, "2026-11")
        self.assertEqual(rows, [
            ("식비", 50000, 20000, 30000),
            ("전체", 100000, 20000, 80000),
        ])

    def test_unset_monthly_and_category_budget(self):
        self.cfg["budget"]["monthly"] = None
        self.cfg["budget"]["by_category"] = {"식비": None}
        self._add_expense("2026-11-10", 12000, category="식비")

        rows = budget.budget_table(self.store, self.cfg, "2026-11")
        self.assertEqual(rows, [
            ("식비", None, 12000, None),
            ("전체", None, 12000, None),
        ])

    def test_empty_store_and_empty_by_category(self):
        self.cfg["budget"]["monthly"] = 100000
        self.cfg["budget"]["by_category"] = {}
        self.assertEqual(
            budget.budget_table(self.store, self.cfg, "2026-11"),
            [("전체", 100000, 0, 100000)],
        )

    def test_invalid_budget_raises(self):
        for bad in (-1, True, "100000"):
            with self.subTest(monthly=bad):
                cfg = copy.deepcopy(self.cfg)
                cfg["budget"]["monthly"] = bad
                with self.assertRaises(ValueError):
                    budget.budget_table(self.store, cfg, "2026-11")

        for bad in (-1, True, "50000"):
            with self.subTest(category_limit=bad):
                cfg = copy.deepcopy(self.cfg)
                cfg["budget"]["by_category"] = {"식비": bad}
                with self.assertRaises(ValueError):
                    budget.budget_table(self.store, cfg, "2026-11")

    def test_does_not_mutate_store_or_cfg(self):
        self.cfg["budget"]["by_category"] = {"식비": 50000}
        self._add_expense("2026-11-10", 10000, category="식비")
        before_data = copy.deepcopy(self.store.data)
        before_cfg = copy.deepcopy(self.cfg)

        budget.budget_table(self.store, self.cfg, "2026-11")
        self.assertEqual(self.store.data, before_data)
        self.assertEqual(self.cfg, before_cfg)


if __name__ == "__main__":
    unittest.main()