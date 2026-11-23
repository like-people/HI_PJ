"""명령 묶음 `budget` 확장 필수 명령(category·unpaid) 테스트. 담당: 기능 5(이정배)."""

import unittest

from helpers import NAMES, StoreCase
from moim import cli

KIM, LEE, PARK = NAMES


class TestBudgetExtendedCommands(StoreCase):
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

    def test_category_table_and_unset(self):
        self.cfg["budget"]["by_category"] = {"식비": 50000, "교통": None}
        self._add_expense("2026-11-10", 40001, category="식비")
        changed, text = self._run("budget", "category", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertIn("식비", text)
        self.assertIn("40,001", text)
        self.assertIn("경고", text)
        self.assertIn("교통", text)
        self.assertIn("미설정", text)

        self.cfg["budget"]["by_category"] = {}
        changed, text = self._run("budget", "category", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertIn("설정되어 있지 않습니다", text)

    def test_unpaid_list_full_paid_and_unset(self):
        self._run("budget", "pay", KIM, "20000", "--date", "2026-11-02")
        changed, text = self._run("budget", "unpaid", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertNotIn(KIM, text)
        self.assertIn(LEE, text)
        self.assertIn(PARK, text)
        self.assertIn("20,000", text)

        self._run("budget", "pay", LEE, "20000", "--date", "2026-11-03")
        self._run("budget", "pay", PARK, "20000", "--date", "2026-11-04")
        changed, text = self._run("budget", "unpaid", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertIn("미납자가 없습니다", text)

        self.cfg["dues"]["monthly"] = None
        changed, text = self._run("budget", "unpaid", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertIn("설정되어 있지 않습니다", text)


if __name__ == "__main__":
    unittest.main()