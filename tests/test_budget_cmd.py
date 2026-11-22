"""명령 묶음 `budget` CLI 테스트. 담당: 기능 5(이정배)."""

import unittest

from helpers import NAMES, StoreCase
from moim import cli

KIM, LEE, PARK = NAMES


class TestBudgetCommands(StoreCase):
    def _add_expense(self, date, amount, category="식비"):
        self.store.data["expenses"].append({
            "id": self.store.new_id(),
            "date": date,
            "payer": KIM,
            "amount": amount,
            "members": [KIM, LEE, PARK],
            "category": category,
            "memo": "",
            "deleted": False,
        })

    def _run(self, *argv):
        args = cli.build_parser().parse_args(list(argv))
        lines = []
        changed = cli.run(args, self.cfg, self.store, out=lines.append)
        return changed, "\n".join(lines)

    def test_status_normal_and_unset(self):
        self._add_expense("2026-11-10", 30000)
        changed, text = self._run("budget", "status", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertIn("100,000원", text)
        self.assertIn("30,000원", text)
        self.assertIn("70,000원", text)
        self.assertIn("정상", text)

        self.cfg["budget"]["monthly"] = None
        changed, text = self._run("budget", "status", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertIn("미설정", text)

    def test_category_table_and_empty(self):
        self.cfg["budget"]["by_category"] = {"식비": 50000, "교통": 20000}
        self._add_expense("2026-11-10", 40000, category="식비")
        changed, text = self._run("budget", "category", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertIn("식비", text)
        self.assertIn("경고", text)
        self.assertIn("교통", text)

        self.cfg["budget"]["by_category"] = {}
        changed, text = self._run("budget", "category", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertIn("설정되어 있지 않습니다", text)

    def test_forecast(self):
        self._add_expense("2026-11-10", 50000)
        changed, text = self._run("budget", "forecast", "--month", "2026-11", "--today", "2026-11-15")
        self.assertFalse(changed)
        self.assertIn("100,000원", text)

    def test_pay_and_balance(self):
        changed, text = self._run(
            "budget", "pay", KIM, "20,000", "--date", "2026-11-02", "--memo", "11월 회비"
        )
        self.assertTrue(changed)
        self.assertIn(KIM, text)
        self.assertIn("20,000원", text)
        self.assertEqual(len(self.store.data["payments"]), 1)

        self._add_expense("2026-11-12", 9000)
        changed, text = self._run("budget", "balance")
        self.assertFalse(changed)
        self.assertIn("11,000원", text)

        changed, text = self._run("budget", "balance", "--until", "2026-11-05")
        self.assertFalse(changed)
        self.assertIn("20,000원", text)

    def test_unpaid_list_and_unset(self):
        self._run("budget", "pay", KIM, "20000", "--date", "2026-11-02")
        changed, text = self._run("budget", "unpaid", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertNotIn(KIM, text)
        self.assertIn(LEE, text)
        self.assertIn(PARK, text)

        self.cfg["dues"]["monthly"] = None
        changed, text = self._run("budget", "unpaid", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertIn("설정되어 있지 않습니다", text)

    def test_table_and_usage(self):
        self.cfg["budget"]["by_category"] = {"식비": 60000}
        self._add_expense("2026-11-10", 40000, category="식비")
        changed, text = self._run("budget", "table", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertIn("식비", text)
        self.assertIn("합계", text)
        self.assertIn("100,000", text)

        changed, text = self._run("budget")
        self.assertFalse(changed)
        self.assertIn("사용법:", text)


if __name__ == "__main__":
    unittest.main()