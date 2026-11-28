"""다음 달 예산 제안(suggest_budget) 테스트. 담당: 기능 5(이정배)."""

import copy
import unittest

from helpers import NAMES, StoreCase
from moim.features import budget

KIM, LEE, PARK = NAMES


class TestSuggestBudget(StoreCase):
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

    def test_exact_multiple_of_thousand(self):
        self._add_expense("2026-09-10", 20000)
        self._add_expense("2026-10-10", 30000)
        self._add_expense("2026-11-10", 40000)
        # 평균 30,000원 -> 30,000원
        self.assertEqual(budget.suggest_budget(self.store, "2026-11"), 30000)

    def test_rounds_up_to_nearest_thousand(self):
        self._add_expense("2026-09-10", 30000)
        self._add_expense("2026-10-10", 30000)
        self._add_expense("2026-11-10", 30001)
        # 합계 90,001원 -> 평균 30,000.33...원 -> 천 원 단위 올림 31,000원
        self.assertEqual(budget.suggest_budget(self.store, "2026-11"), 31000)

    def test_cross_year_boundary_three_months(self):
        self._add_expense("2025-11-30", 90000)  # 범위 밖(4개월 전)
        self._add_expense("2025-12-15", 30000)
        self._add_expense("2026-01-15", 30000)
        self._add_expense("2026-02-15", 40000)
        self._add_expense("2026-03-01", 90000)  # 범위 밖(다음 달)
        # 최근 3개월(2025-12~2026-02) 합계 100,000원 -> 평균 33,333.33... -> 34,000원
        self.assertEqual(budget.suggest_budget(self.store, "2026-02"), 34000)

    def test_zero_spending_and_excludes_deleted(self):
        self.assertEqual(budget.suggest_budget(self.store, "2026-11"), 0)
        self._add_expense("2026-11-10", 50000, deleted=True)
        self.assertEqual(budget.suggest_budget(self.store, "2026-11"), 0)

    def test_invalid_month_raises_and_does_not_mutate_store(self):
        with self.assertRaises(ValueError):
            budget.suggest_budget(self.store, "2026-13")

        self._add_expense("2026-11-10", 30000)
        before = copy.deepcopy(self.store.data)
        budget.suggest_budget(self.store, "2026-11")
        self.assertEqual(self.store.data, before)


if __name__ == "__main__":
    unittest.main()
