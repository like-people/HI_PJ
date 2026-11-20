
import json
import tempfile
import unittest
from pathlib import Path

from moim.common.store import Store
from moim.features.transfer_io import (
    backup_all,
    file_total,
    restore_all,
)


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

    def test_backup_and_restore_all(self):
        store = Store(self.root / "data.json")
        store.data["members"] = [
            {"name": "철수", "joined": "2026-01-01", "left": None}
        ]
        store.data["expenses"] = [
            {
                "id": 1,
                "date": "2026-11-19",
                "payer": "철수",
                "amount": 1000,
                "members": ["철수"],
                "deleted": False,
            }
        ]
        store.data["next_id"] = 2
        expected = json.loads(json.dumps(store.data))

        backup_path = self.root / "backup" / "all.json"
        backup_all(store, backup_path)

        store.data["members"] = []
        store.data["expenses"] = []
        store.data["next_id"] = 1

        restore_all(store, backup_path)
        self.assertEqual(store.data, expected)

    def test_restore_all_invalid_backup(self):
        store = Store(self.root / "data.json")
        path = self.root / "invalid.json"
        path.write_text("[]", encoding="utf-8")

        with self.assertRaises(ValueError):
            restore_all(store, path)


if __name__ == "__main__":
    unittest.main()
