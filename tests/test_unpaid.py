
import unittest

from helpers import NAMES, StoreCase
from moim.features import budget

KIM, LEE, PARK = NAMES


class TestUnpaid(StoreCase):

    def test_no_payment(self):
        result = budget.unpaid(
            self.store, self.cfg, "2026-11"
        )
        self.assertEqual(result, [
            (KIM, 0, 20000),
            (LEE, 0, 20000),
            (PARK, 0, 20000),
        ])

    def test_partial_payment(self):
        self.store.data["payments"].append({
            "date": "2026-11-02",
            "member": LEE,
            "amount": 5000,
            "memo": "",
            "source": "manual",
        })

        result = budget.unpaid(
            self.store, self.cfg, "2026-11"
        )
        self.assertIn((LEE, 5000, 15000), result)

    def test_full_payment(self):
        self.store.data["payments"].append({
            "date": "2026-11-02",
            "member": KIM,
            "amount": 20000,
        })

        result = budget.unpaid(
            self.store, self.cfg, "2026-11"
        )
        self.assertNotIn((KIM, 20000, 0), result)

    def test_multiple_payments(self):
        for amount in (5000, 10000):
            self.store.data["payments"].append({
                "date": "2026-11-02",
                "member": KIM,
                "amount": amount,
            })

        result = budget.unpaid(
            self.store, self.cfg, "2026-11"
        )
        self.assertIn((KIM, 15000, 5000), result)

    def test_other_month_excluded(self):
        self.store.data["payments"].append({
            "date": "2026-10-31",
            "member": KIM,
            "amount": 20000,
        })

        result = budget.unpaid(
            self.store, self.cfg, "2026-11"
        )
        self.assertIn((KIM, 0, 20000), result)

    def test_unset_dues(self):
        self.cfg["dues"]["monthly"] = None

        self.assertEqual(
            budget.unpaid(self.store, self.cfg, "2026-11"),
            []
        )


if __name__ == "__main__":
    unittest.main()
