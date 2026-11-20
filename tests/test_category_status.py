"""분류별 예산 상태(category_status) 테스트. 담당: 기능 5(이정배)."""

import copy
import unittest

from helpers import NAMES, StoreCase
from moim.features import budget

KIM, LEE, PARK = NAMES


class TestCategoryStatus(StoreCase):
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

    def test_normal_warn_over_and_zero_spent(self):
        self.cfg["budget"]["by_category"] = {
            "식비": 50000,
            "장소": 30000,
            "교통": 20000,
            "기타": 10000,
        }
        self._add_expense("2026-11-05", 20000, category="식비")
        self._add_expense("2026-11-10", 24000, category="장소")  # 80% 경계
        self._add_expense("2026-11-12", 25000, category="교통")  # 초과

        result = budget.category_status(self.store, self.cfg, "2026-11")
        self.assertEqual(list(result.keys()), ["식비", "장소", "교통", "기타"])
        self.assertEqual(result["식비"], {
            "budget": 50000,
            "spent": 20000,
            "remaining": 30000,
            "over": False,
            "warn": False,
        })
        self.assertEqual(result["장소"], {
            "budget": 30000,
            "spent": 24000,
            "remaining": 6000,
            "over": False,
            "warn": True,
        })
        self.assertEqual(result["교통"], {
            "budget": 20000,
            "spent": 25000,
            "remaining": -5000,
            "over": True,
            "warn": True,
        })
        self.assertEqual(result["기타"], {
            "budget": 10000,
            "spent": 0,
            "remaining": 10000,
            "over": False,
            "warn": False,
        })

    def test_excludes_deleted_other_months_and_unbudgeted_categories(self):
        self.cfg["budget"]["by_category"] = {"식비": 50000}
        self._add_expense("2026-10-31", 10000, category="식비")
        self._add_expense("2026-11-10", 15000, category="식비")
        self._add_expense("2026-11-11", 30000, category="식비", deleted=True)
        self._add_expense("2026-11-12", 20000, category="간식")
        self._add_expense("2026-11-13", 10000, category=None)

        result = budget.category_status(self.store, self.cfg, "2026-11")
        self.assertEqual(list(result.keys()), ["식비"])
        self.assertEqual(result["식비"]["spent"], 15000)
        self.assertEqual(result["식비"]["remaining"], 35000)

    def test_empty_or_unset_by_category(self):
        self.cfg["budget"]["by_category"] = {}
        self._add_expense("2026-11-10", 10000, category="식비")
        self.assertEqual(budget.category_status(self.store, self.cfg, "2026-11"), {})

        self.cfg["budget"]["by_category"] = {"식비": None}
        result = budget.category_status(self.store, self.cfg, "2026-11")
        self.assertEqual(result["식비"], {
            "budget": None,
            "spent": 10000,
            "remaining": None,
            "over": False,
            "warn": False,
        })

    def test_invalid_category_budget_or_warn_ratio_raises(self):
        for bad in (-100, True, "50000"):
            with self.subTest(limit=bad):
                cfg = copy.deepcopy(self.cfg)
                cfg["budget"]["by_category"] = {"식비": bad}
                with self.assertRaises(ValueError):
                    budget.category_status(self.store, cfg, "2026-11")

        for bad_ratio in (-0.1, 1.2, True, "0.8"):
            with self.subTest(warn_ratio=bad_ratio):
                cfg = copy.deepcopy(self.cfg)
                cfg["budget"]["by_category"] = {"식비": 50000}
                cfg["warn_ratio"] = bad_ratio
                with self.assertRaises(ValueError):
                    budget.category_status(self.store, cfg, "2026-11")

    def test_does_not_mutate_store_or_cfg(self):
        self.cfg["budget"]["by_category"] = {"식비": 50000}
        self._add_expense("2026-11-10", 10000, category="식비")
        before_data = copy.deepcopy(self.store.data)
        before_cfg = copy.deepcopy(self.cfg)

        budget.category_status(self.store, self.cfg, "2026-11")
        self.assertEqual(self.store.data, before_data)
        self.assertEqual(self.cfg, before_cfg)


if __name__ == "__main__":
    unittest.main()