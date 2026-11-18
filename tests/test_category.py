"""기능 2: 분류 조회 공통 함수(category_of, category_totals) 테스트.

expenses_in 은 기능 3 담당이 채우므로, 여기서는 mock 으로 바꿔 분류 합계만 확인한다.
실행: python -m unittest discover -s tests -v
"""

import unittest
from unittest import mock

from helpers import NAMES, StoreCase

from moim.common import queries
from moim.common.queries import category_of, category_totals

KIM = NAMES[0]


def expense(eid, amount, category=None):
    return {"id": eid, "date": "2026-11-10", "payer": KIM, "amount": amount,
            "members": list(NAMES), "category": category, "memo": ""}


class CategoryOf(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(category_of(expense(1, 1000, "식비")), "식비")

    def test_none_is_uncategorized(self):
        self.assertEqual(category_of(expense(1, 1000, None)), "미분류")

    def test_empty_string_is_uncategorized(self):
        self.assertEqual(category_of(expense(1, 1000, "")), "미분류")

    def test_missing_key_is_uncategorized(self):
        e = expense(1, 1000)
        del e["category"]
        self.assertEqual(category_of(e), "미분류")

    def test_direct_uncategorized_is_same(self):
        self.assertEqual(category_of(expense(1, 1000, "미분류")), "미분류")


class CategoryTotals(StoreCase):
    def totals(self, expenses):
        with mock.patch.object(queries, "expenses_in", return_value=expenses):
            return category_totals(self.store, "2026-11-01", "2026-11-30")

    def test_count_and_amount(self):
        result = self.totals([expense(1, 6000, "식비"), expense(2, 3000, "식비"), expense(3, 9000, "교통")])
        self.assertEqual(result, {"식비": {"count": 2, "amount": 9000}, "교통": {"count": 1, "amount": 9000}})

    def test_sorted_by_amount_desc(self):
        result = self.totals([expense(1, 1000, "가"), expense(2, 9000, "나"), expense(3, 5000, "다")])
        self.assertEqual(list(result), ["나", "다", "가"])

    def test_tie_sorted_by_name(self):
        result = self.totals([expense(1, 6000, "식비"), expense(2, 6000, "교통")])
        self.assertEqual(list(result), ["교통", "식비"])

    def test_none_and_direct_uncategorized_merge(self):
        result = self.totals([expense(1, 1000, None), expense(2, 3000, "미분류")])
        self.assertEqual(result, {"미분류": {"count": 2, "amount": 4000}})

    def test_empty(self):
        self.assertEqual(self.totals([]), {})


if __name__ == "__main__":
    unittest.main()