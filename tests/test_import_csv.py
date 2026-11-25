import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from moim.common import ledger
from moim.common.store import Store
from moim.features.transfer_io import import_csv


class ImportCsvTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.path = Path(self.temp_dir.name) / "expenses.csv"
        self.store = Store(Path(self.temp_dir.name) / "store.json")

        self.store.data["members"] = [
            {"name": "철수", "joined": "2026-01-01", "left": None},
            {"name": "영희", "joined": "2026-01-01", "left": None},
            {"name": "민수", "joined": "2026-01-01", "left": None},
        ]

    def write_csv(self, rows, headers=None):
        if headers is None:
            headers = ["date", "payer", "amount", "members", "weights"]

        with self.path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    def test_import_csv_normal_and_weights(self):
        self.write_csv([
            {
                "date": "2026-01-10",
                "payer": "철수",
                "amount": "10000",
                "members": "철수;영희",
                "weights": "철수:1;영희:2",
            },
        ])

        result = import_csv(self.store, self.path)

        self.assertEqual(len(result["added"]), 1)
        self.assertEqual(len(self.store.data["expenses"]), 1)
        self.assertEqual(result["errors"], [])

        expense = self.store.data["expenses"][0]
        self.assertEqual(expense["amount"], 10000)
        self.assertEqual(expense["weights"], {"철수": 1, "영희": 2})

    def test_import_csv_preview(self):
        self.write_csv([
            {
                "date": "2026-01-10",
                "payer": "철수",
                "amount": "10000",
                "members": "철수;영희",
                "weights": "",
            },
        ])

        result = import_csv(self.store, self.path, preview=True)

        self.assertEqual(len(result["added"]), 1)
        self.assertEqual(self.store.data["expenses"], [])

    def test_import_csv_duplicates(self):
        self.store.data["expenses"].append({
            "id": 1,
            "date": "2026-01-10",
            "payer": "철수",
            "amount": 10000,
            "members": ["철수", "영희"],
            "weights": None,
            "memo": "",
            "deleted": False,
        })

        self.write_csv([
            {
                "date": "2026-01-10",
                "payer": "철수",
                "amount": "10000",
                "members": "철수;영희",
                "weights": "",
            },
            {
                "date": "2026-01-10",
                "payer": "철수",
                "amount": "10000",
                "members": "철수;영희",
                "weights": "",
            },
        ])

        result = import_csv(self.store, self.path)

        self.assertEqual(len(result["duplicates"]), 2)
        self.assertEqual(len(self.store.data["expenses"]), 1)
        self.assertEqual(result["added"], [])
        self.assertEqual(result["errors"], [])

    def test_import_csv_failed_insert_does_not_mark_seen(self):
        row = {
            "date": "2026-01-10",
            "payer": "철수",
            "amount": "10000",
            "members": "철수;영희",
            "weights": "",
        }
        self.write_csv([row, row])

        original_insert = ledger.insert
        calls = 0

        def fail_once_then_insert(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ValueError("테스트용 등록 실패")
            return original_insert(*args, **kwargs)

        with patch.object(ledger, "insert", side_effect=fail_once_then_insert):
            result = import_csv(self.store, self.path)

        self.assertEqual(result["errors"], [(2, "테스트용 등록 실패")])
        self.assertEqual(len(result["added"]), 1)
        self.assertEqual(result["duplicates"], [])
        self.assertEqual(len(self.store.data["expenses"]), 1)

    def test_import_csv_errors(self):
        self.write_csv([
            {
                "date": "2026-01-10",
                "payer": "철수",
                "amount": "10000",
                "members": "철수;영희",
                "weights": "잘못된형식",
            },
            {
                "date": "잘못된날짜",
                "payer": "없는사람",
                "amount": "abc",
                "members": "없는사람",
                "weights": "",
            },
        ])

        result = import_csv(self.store, self.path)

        self.assertEqual(len(result["errors"]), 2)
        self.assertEqual(self.store.data["expenses"], [])

    def test_import_csv_mapping_and_empty_file(self):
        self.write_csv(
            [{
                "날짜": "2026-01-10",
                "결제자": "철수",
                "금액": "10000",
                "참여자": "철수;영희",
            }],
            headers=["날짜", "결제자", "금액", "참여자"],
        )

        # CSV 원본 열 이름 -> 내부 필드 이름
        mapping = {
            "날짜": "date",
            "결제자": "payer",
            "금액": "amount",
            "참여자": "members",
        }

        result = import_csv(self.store, self.path, mapping=mapping)

        self.assertEqual(len(result["added"]), 1)
        self.assertEqual(len(self.store.data["expenses"]), 1)
        self.assertEqual(result["errors"], [])

        self.path.write_text("", encoding="utf-8")
        result = import_csv(self.store, self.path)

        self.assertEqual(result["added"], [])
        self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
