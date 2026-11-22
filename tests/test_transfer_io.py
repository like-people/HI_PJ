
import json
import tempfile
import unittest
from pathlib import Path

from moim.features.transfer_io import file_total


class TransferIOTests(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def test_file_total_csv(self):
        path = self.root / "expenses.csv"
        path.write_text(
            'amount\n1000\n"1,500"\n',
            encoding="utf-8-sig",
        )
        self.assertEqual(file_total(path), (2, 2500))

    def test_file_total_csv_without_amount(self):
        path = self.root / "expenses.csv"
        path.write_text(
            "date,payer\n2026-11-19,철수\n",
            encoding="utf-8-sig",
        )
        with self.assertRaises(ValueError):
            file_total(path)

    def test_file_total_csv_with_empty_amount(self):
        path = self.root / "expenses.csv"
        path.write_text(
            "amount,memo\n1000,정상 거래\n,금액 누락\n",
            encoding="utf-8-sig",
        )
        with self.assertRaises(ValueError):
            file_total(path)

    def test_file_total_json_excludes_deleted(self):
        path = self.root / "expenses.json"
        data = {
            "expenses": [
                {"amount": 1000, "deleted": False},
                {"amount": 2000, "deleted": True},
                {"amount": 500},
            ]
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )
        self.assertEqual(file_total(path), (2, 1500))

if __name__ == "__main__":
    unittest.main()
