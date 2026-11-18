"""회비 입금 기록 테스트. 담당: 기능 5(이정배)."""

import datetime as dt
import os

from helpers import NAMES, StoreCase

from moim.features.budget import record_payment


class RecordPaymentTests(StoreCase):
    def test_record_and_return_payment(self):
        payment = record_payment(
            self.store, "2026-11-02", NAMES[0], "20,000", memo="11월 회비"
        )
        expected = {
            "date": "2026-11-02",
            "member": NAMES[0],
            "amount": 20000,
            "memo": "11월 회비",
            "source": "manual",
        }
        self.assertEqual(payment, expected)
        self.assertEqual(self.store.data["payments"], [expected])

    def test_default_memo(self):
        payment = record_payment(
            self.store, "2026-11-02", NAMES[0], 1000
        )
        self.assertEqual(payment["memo"], "")

    def test_date_object(self):
        payment = record_payment(
            self.store, dt.date(2026, 11, 2), NAMES[0], 1000
        )
        self.assertEqual(payment["date"], "2026-11-02")

    def test_amount_rounding(self):
        for amount, expected in (("1,234.5원", 1235), ("1,234.4원", 1234)):
            with self.subTest(amount=amount):
                payment = record_payment(
                    self.store, "2026-11-02", NAMES[0], amount
                )
                self.assertEqual(payment["amount"], expected)

    def test_invalid_date_does_not_add_payment(self):
        with self.assertRaises(ValueError):
            record_payment(self.store, "2026-02-30", NAMES[0], 1000)
        self.assertEqual(self.store.data["payments"], [])

    def test_unknown_member_does_not_add_payment(self):
        with self.assertRaises(ValueError):
            record_payment(self.store, "2026-11-02", "없는회원", 1000)
        self.assertEqual(self.store.data["payments"], [])

    def test_invalid_amount_does_not_add_payment(self):
        for amount in (0, -1000, "0.4", "금액아님", True):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    record_payment(
                        self.store, "2026-11-02", NAMES[0], amount
                    )
                self.assertEqual(self.store.data["payments"], [])

    def test_append_without_expense_id_or_file_save(self):
        first = record_payment(
            self.store, "2026-11-02", NAMES[0], 1000
        )
        second = record_payment(
            self.store, "2026-11-03", NAMES[1], 2000
        )
        self.assertEqual(self.store.data["payments"], [first, second])
        self.assertNotIn("id", first)
        self.assertNotIn("id", second)
        self.assertEqual(self.store.data["next_id"], 1)
        self.assertEqual(self.store.data["expenses"], [])
        self.assertFalse(os.path.exists(self.store.path))
