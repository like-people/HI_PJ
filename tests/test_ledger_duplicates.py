
"""기능 6: 같은 조건의 중복 지출 검색 검사."""

import datetime as dt
import unittest

from helpers import StoreCase
from moim.common.ledger import duplicates


class LedgerDuplicatesTests(StoreCase):
    def setUp(self):
        super().setUp()
        self.store.data["expenses"] = [
            {
                "id": 3,
                "date": "2026-11-18",
                "payer": "김민수",
                "amount": 10000,
            },
            {
                "id": 1,
                "date": "2026-11-18",
                "payer": "김민수",
                "amount": 10000,
            },
            {
                "id": 2,
                "date": "2026-11-18",
                "payer": "이서연",
                "amount": 10000,
            },
            {
                "id": 4,
                "date": "2026-11-17",
                "payer": "김민수",
                "amount": 10000,
            },
            {
                "id": 5,
                "date": "2026-11-18",
                "payer": "김민수",
                "amount": 20000,
            },
            {
                "id": 6,
                "date": "2026-11-18",
                "payer": "김민수",
                "amount": 10000,
                "deleted": True,
            },
        ]


    def test_matching_expenses_sorted_by_id(self):
        self.assertEqual(
            duplicates(self.store, "2026-11-18", "김민수", 10000),
            [1, 3],
        )


    def test_exclude_different_date(self):
        self.assertEqual(
            duplicates(self.store, "2026-11-19", "김민수", 10000),
            [],
        )


    def test_exclude_different_payer(self):
        self.assertEqual(
            duplicates(self.store, "2026-11-18", "박지훈", 10000),
            [],
        )


    def test_exclude_different_amount(self):
        self.assertEqual(
            duplicates(self.store, "2026-11-18", "김민수", 30000),
            [],
        )


    def test_exclude_deleted_expenses(self):
        result = duplicates(self.store, "2026-11-18", "김민수", 10000)
        self.assertNotIn(6, result)


    def test_exclude_id(self):
        self.assertEqual(
            duplicates(
                self.store, "2026-11-18", "김민수", 10000, exclude_id=1
            ),
            [3],
        )


    def test_date_object(self):
        self.assertEqual(
            duplicates(
                self.store, dt.date(2026, 11, 18), "김민수", 10000
            ),
            [1, 3],
        )


if __name__ == "__main__":
    unittest.main()
