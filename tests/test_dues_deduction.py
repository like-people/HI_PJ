"""기능 5: 회비 부족액 계산 테스트."""

import copy
import unittest

from helpers import NAMES, StoreCase
from moim.features import budget

KIM, LEE, PARK = NAMES


class TestDuesDeduction(StoreCase):
    def test_no_payment(self):
        """입금이 없으면 회원별 월 회비 전액을 반환한다."""
        self.assertEqual(
            budget.dues_deduction(self.store, self.cfg, "2026-11"),
            {KIM: 20000, LEE: 20000, PARK: 20000},
        )

    def test_partial_full_and_overpayment(self):
        """분할 입금을 합산하고 완납자·초과 납부자는 제외한다."""
        self.store.data["payments"] = [
            {
                "date": "2026-11-02",
                "member": KIM,
                "amount": 5000,
                "memo": "",
                "source": "manual",
            },
            {
                "date": "2026-11-10",
                "member": KIM,
                "amount": 10000,
                "memo": "",
                "source": "bank",
            },
            {
                "date": "2026-11-02",
                "member": LEE,
                "amount": 20000,
                "memo": "",
                "source": "manual",
            },
            {
                "date": "2026-11-02",
                "member": PARK,
                "amount": 25000,
                "memo": "",
                "source": "bank",
            },
        ]

        self.assertEqual(
            budget.dues_deduction(self.store, self.cfg, "2026-11"),
            {KIM: 5000},
        )

    def test_no_unpaid_members(self):
        """모두 완납하면 빈 딕셔너리를 반환한다."""
        self.store.data["payments"] = [
            {
                "date": "2026-11-02",
                "member": name,
                "amount": 20000,
                "memo": "",
                "source": "manual",
            }
            for name in NAMES
        ]

        self.assertEqual(
            budget.dues_deduction(self.store, self.cfg, "2026-11"),
            {},
        )

    def test_unset_dues(self):
        """월 회비가 미설정이면 빈 딕셔너리를 반환한다."""
        self.cfg["dues"]["monthly"] = None

        self.assertEqual(
            budget.dues_deduction(self.store, self.cfg, "2026-11"),
            {},
        )

    def test_data_unchanged(self):
        """계산 전후 저장소 자료와 설정이 바뀌지 않는다."""
        before_data = copy.deepcopy(self.store.data)
        before_cfg = copy.deepcopy(self.cfg)

        budget.dues_deduction(self.store, self.cfg, "2026-11")

        self.assertEqual(self.store.data, before_data)
        self.assertEqual(self.cfg, before_cfg)


if __name__ == "__main__":
    unittest.main()
