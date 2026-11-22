"""모임 통장 잔고(treasury_balance) 테스트. 담당: 기능 5(이정배)."""

import copy
import datetime as dt
import unittest

from helpers import NAMES, StoreCase
from moim.features import budget

KIM, LEE, PARK = NAMES


class TestTreasuryBalance(StoreCase):
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

    def test_empty_store_is_zero(self):
        self.assertEqual(budget.treasury_balance(self.store), 0)
        self.assertEqual(budget.treasury_balance(self.store, until="2026-11-30"), 0)

    def test_payments_minus_expenses(self):
        budget.record_payment(self.store, "2026-11-02", KIM, 20000)
        budget.record_payment(self.store, "2026-11-05", LEE, 20000)
        self._add_expense("2026-11-10", 15000)
        self._add_expense("2026-11-12", 9000)

        self.assertEqual(budget.treasury_balance(self.store), 16000)

    def test_negative_balance_when_expenses_exceed_payments(self):
        budget.record_payment(self.store, "2026-11-02", KIM, 10000)
        self._add_expense("2026-11-10", 25000)

        self.assertEqual(budget.treasury_balance(self.store), -15000)

    def test_until_date_is_inclusive(self):
        budget.record_payment(self.store, "2026-11-02", KIM, 20000)
        self._add_expense("2026-11-10", 8000)
        budget.record_payment(self.store, "2026-11-15", LEE, 20000)
        self._add_expense("2026-11-20", 15000)

        self.assertEqual(budget.treasury_balance(self.store, until="2026-11-01"), 0)
        self.assertEqual(budget.treasury_balance(self.store, until="2026-11-10"), 12000)
        self.assertEqual(
            budget.treasury_balance(self.store, until=dt.date(2026, 11, 15)), 32000
        )
        self.assertEqual(budget.treasury_balance(self.store, until="2026-11-20"), 17000)

    def test_excludes_deleted_expenses(self):
        budget.record_payment(self.store, "2026-11-02", KIM, 30000)
        self._add_expense("2026-11-10", 10000)
        self._add_expense("2026-11-12", 12000, deleted=True)

        self.assertEqual(budget.treasury_balance(self.store), 20000)

    def test_invalid_until_raises_value_error(self):
        with self.assertRaises(ValueError):
            budget.treasury_balance(self.store, until="2026-02-30")

    def test_does_not_mutate_store(self):
        budget.record_payment(self.store, "2026-11-02", KIM, 20000)
        self._add_expense("2026-11-10", 9000)
        before = copy.deepcopy(self.store.data)

        budget.treasury_balance(self.store, until="2026-11-10")
        self.assertEqual(self.store.data, before)


if __name__ == "__main__":
    unittest.main()