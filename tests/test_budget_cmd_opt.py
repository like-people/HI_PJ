"""명령 묶음 `budget` 선택 명령(forecast·table) 테스트. 담당: 기능 5(이정배)."""

import unittest

from helpers import NAMES, StoreCase
from moim import cli

KIM, LEE, PARK = NAMES


class TestBudgetOptionalCommands(StoreCase):
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

    def test_forecast_output(self):
        self._add_expense("2026-11-10", 50000)
        changed, text = self._run(
            "budget", "forecast", "--month", "2026-11", "--today", "2026-11-15"
        )
        self.assertFalse(changed)
        self.assertIn("2026-11 월말 예상 지출(2026-11-15 기준): 100,000원", text)

    def test_table_output_and_unset_budget(self):
        self.cfg["budget"]["by_category"] = {"식비": 60000}
        self._add_expense("2026-11-10", 40000, category="식비")
        changed, text = self._run("budget", "table", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertIn("식비", text)
        self.assertIn("합계", text)
        self.assertIn("100,000", text)
        self.assertIn("40,000", text)

        self.cfg["budget"]["monthly"] = None
        self.cfg["budget"]["by_category"] = {"식비": None}
        changed, text = self._run("budget", "table", "--month", "2026-11")
        self.assertFalse(changed)
        self.assertIn("-", text)
        self.assertIn("합계", text)


if __name__ == "__main__":
    unittest.main()