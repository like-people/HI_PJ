"""명령 묶음 `budget import-bank` CLI 테스트. 담당: 기능 5(이정배)."""

import csv
import json
import unittest
from pathlib import Path

from helpers import NAMES, StoreCase
from moim import cli
from moim.common.store import Store
from moim.features.budget import BANK_COLUMNS

KIM, LEE, PARK = NAMES


class TestBudgetImportBankCommand(StoreCase):
    def _write_bank(self, rows, encoding="utf-8"):
        path = self.path("bank.csv")
        with open(path, "w", encoding=encoding, newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(BANK_COLUMNS)
            writer.writerows(rows)
        return path

    def test_cli_saves_success_and_does_not_save_again_for_duplicates(self):
        path = self._write_bank([
            ("2026.11.03", "11:00", "식사", "1000", "", "-1000"),
            ("2026.11.03", "11:30", "없는 회원", "", "1000", "0"),
        ])
        config_path = Path(self.path("config.json"))
        config_path.write_text(
            json.dumps({"data_file": self.path("data.json"), "treasurer": LEE}),
            encoding="utf-8",
        )
        self.store.save()

        args = ["--config", str(config_path), "budget", "import-bank", path, "--treasurer", KIM]
        output = []
        self.assertEqual(cli.main(args, output.append), 0)
        self.assertIn("지출 1건", output[0])
        self.assertIn("오류 3줄", output[1])

        reloaded = Store(self.path("data.json")).load()
        self.assertEqual(reloaded.data["expenses"][0]["payer"], KIM)
        backups = reloaded.backups()

        output.clear()
        self.assertEqual(cli.main(args[:-2], output.append), 0)
        self.assertIn("중복으로 건너뛴 줄: 2", output)
        self.assertEqual(reloaded.backups(), backups)

    def test_cli_uses_configured_treasurer(self):
        path = self._write_bank([("2026.11.03", "11:00", "식사", "1000", "", "-1000")])
        args = cli.build_parser().parse_args(["budget", "import-bank", path])
        output = []
        self.assertTrue(cli.run(args, {"treasurer": LEE}, self.store, out=output.append))
        self.assertEqual(self.store.data["expenses"][0]["payer"], LEE)
        self.assertIn("지출 1건, 회비 입금 0건", output[0])

    def test_cli_returns_false_when_only_errors(self):
        path = self._write_bank([("2026.11.03", "11:30", "없는 회원", "", "1000", "0")])
        args = cli.build_parser().parse_args(["budget", "import-bank", path])
        output = []
        self.assertFalse(cli.run(args, {"treasurer": LEE}, self.store, out=output.append))
        self.assertIn("지출 0건, 회비 입금 0건", output[0])
        self.assertIn("오류 2줄", output[1])


if __name__ == "__main__":
    unittest.main()