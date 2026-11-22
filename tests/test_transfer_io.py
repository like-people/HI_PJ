
"""기능 6. 가져오기·내보내기 file_total 및 roundtrip_check 테스트."""

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from moim.features.transfer_io import file_total, roundtrip_check


class TransferIOTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_file_total_csv(self):
        path = self.root / "expenses.csv"
        path.write_text(
            "id,date,payer,amount,members,weights,category,memo\n"
            "1,2026-11-19,철수,3000,철수;영희,,식비,점심\n"
            "2,2026-11-20,영희,5000,철수;영희,,카페,커피\n",
            encoding="utf-8",
        )

        self.assertEqual(file_total(path), (2, 8000))

    def test_file_total_csv_without_amount(self):
        path = self.root / "expenses.csv"
        path.write_text(
            "id,date,payer,members,weights,category,memo\n"
            "1,2026-11-19,철수,철수;영희,,식비,점심\n",
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            file_total(path)

    def test_file_total_csv_with_empty_amount(self):
        path = self.root / "expenses.csv"
        path.write_text(
            "id,date,payer,amount,members,weights,category,memo\n"
            "1,2026-11-19,철수,,철수;영희,,식비,점심\n",
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            file_total(path)

    def test_file_total_json_excludes_deleted(self):
        path = self.root / "expenses.json"
        path.write_text(
            json.dumps(
                {
                    "expenses": [
                        {"amount": 3000, "deleted": False},
                        {"amount": 5000, "deleted": True},
                        {"amount": 2000},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        self.assertEqual(file_total(path), (2, 5000))

    def test_file_total_json_missing_amount(self):
        path = self.root / "expenses.json"
        path.write_text(
            json.dumps(
                {
                    "expenses": [
                        {"deleted": False},
                        {"amount": 3000},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            file_total(path)

    def test_roundtrip_check_matches_export(self):
        from moim.common.store import Store

        store = Store(self.root / "store.json")
        store.data["expenses"] = [
            {
                "id": 1,
                "date": "2026-11-19",
                "payer": "철수",
                "amount": 3000,
                "members": ["철수", "영희"],
                "weights": None,
                "category": "식비",
                "memo": "점심",
            },
        ]

        path = self.root / "roundtrip.csv"
        result = roundtrip_check(store, path)

        self.assertEqual(result, [])

    def test_roundtrip_check_with_filters(self):
        from moim.common.store import Store

        store = Store(self.root / "store.json")
        store.data["expenses"] = [
            {
                "id": 1,
                "date": "2026-11-19",
                "payer": "철수",
                "amount": 3000,
                "members": ["철수", "영희"],
                "weights": None,
                "category": "식비",
                "memo": "점심",
            },
            {
                "id": 2,
                "date": "2026-11-20",
                "payer": "영희",
                "amount": 5000,
                "members": ["철수", "영희"],
                "weights": None,
                "category": "카페",
                "memo": "커피",
            },
        ]

        path = self.root / "roundtrip.csv"
        result = roundtrip_check(
            store,
            path,
            start="2026-11-19",
            end="2026-11-19",
            category="식비",
        )

        self.assertEqual(result, [])

    def test_roundtrip_check_returns_different_ids(self):
        from moim.common.store import Store

        store = Store(self.root / "store.json")
        store.data["expenses"] = [
            {
                "id": 1,
                "date": "2026-11-19",
                "payer": "철수",
                "amount": 3000,
                "members": ["철수", "영희"],
                "weights": None,
                "category": "식비",
                "memo": "점심",
            },
        ]

        path = self.root / "roundtrip.csv"

        def wrong_export(store, path, start=None, end=None, category=None):
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "id", "date", "payer", "amount",
                    "members", "weights", "category", "memo",
                ])
                writer.writerow([
                    "1", "2026-11-19", "철수", "4000",
                    "철수;영희", "", "식비", "점심",
                ])

        with patch(
            "moim.features.transfer_io.export_csv",
            side_effect=wrong_export,
        ):
            result = roundtrip_check(store, path)

        self.assertEqual(result, ["1"])

    def test_roundtrip_check_detects_duplicate_ids(self):
        from moim.common.store import Store

        store = Store(self.root / "store.json")
        store.data["expenses"] = [
            {
                "id": 1,
                "date": "2026-11-19",
                "payer": "철수",
                "amount": 3000,
                "members": ["철수", "영희"],
                "weights": None,
                "category": "식비",
                "memo": "점심",
            },
        ]

        path = self.root / "roundtrip.csv"

        def duplicate_export(store, path, start=None, end=None, category=None):
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "id", "date", "payer", "amount",
                    "members", "weights", "category", "memo",
                ])
                row = [
                    "1", "2026-11-19", "철수", "3000",
                    "철수;영희", "", "식비", "점심",
                ]
                writer.writerow(row)
                writer.writerow(row)

        with patch(
            "moim.features.transfer_io.export_csv",
            side_effect=duplicate_export,
        ):
            result = roundtrip_check(store, path)

        self.assertEqual(result, ["1"])


if __name__ == "__main__":
    unittest.main()
