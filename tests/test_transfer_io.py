"""기능 6. 가져오기·내보내기 file_total 및 roundtrip_check 테스트."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from moim.features.transfer_io import (
    export_csv,
    file_total,
    roundtrip_check,
)


class TransferIOTests(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def make_expense(self, eid, date, payer, amount, category, memo):
        return {
            "id": eid,
            "date": date,
            "payer": payer,
            "amount": amount,
            "members": ["철수", "영희"],
            "weights": None,
            "category": category,
            "memo": memo,
        }

    def make_store(self, expenses):
        from moim.common.store import Store

        store = Store(self.root / "store.json")
        store.data["expenses"] = expenses
        return store

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

    def test_file_total_csv_bom_and_comma_amount(self):
        path = self.root / "expenses.csv"
        path.write_text(
            "\ufeffid,date,payer,amount,members,weights,category,memo\n"
            '1,2026-11-19,철수,"1,500",철수;영희,,식비,점심\n',
            encoding="utf-8",
        )
        self.assertEqual(file_total(path), (1, 1500))

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

    def test_file_total_json_missing_amount(self):
        path = self.root / "expenses.json"
        data = {
            "expenses": [
                {"payer": "철수"},
            ]
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            file_total(path)

    def test_file_total_json_invalid_root(self):
        path = self.root / "invalid.json"
        path.write_text("123", encoding="utf-8")

        with self.assertRaises(ValueError):
            file_total(path)

    def test_file_total_json_empty_expenses(self):
        path = self.root / "empty.json"
        path.write_text(
            json.dumps({"expenses": []}),
            encoding="utf-8",
        )

        self.assertEqual(file_total(path), (0, 0))

    def test_file_total_json_missing_expenses_key(self):
        path = self.root / "missing_expenses.json"
        data = {
            "items": [
                {"amount": 1000},
            ]
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            file_total(path)

    def test_file_total_json_list_format(self):
        path = self.root / "list.json"
        data = [
            {"amount": 1000},
            {"amount": 2500},
        ]
        path.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )

        self.assertEqual(file_total(path), (2, 3500))

    def test_file_total_json_invalid_row(self):
        path = self.root / "invalid_row.json"
        data = {
            "expenses": [1, 2],
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            file_total(path)

    def test_roundtrip_check_matches_export(self):
        store = self.make_store([
            self.make_expense(
                1, "2026-11-19", "철수", 3000, "식비", "점심"
            ),
        ])

        path = self.root / "roundtrip.csv"
        export_csv(store, path)

        self.assertEqual(roundtrip_check(store, path), [])

    def test_roundtrip_check_with_filters(self):
        store = self.make_store([
            self.make_expense(
                1, "2026-11-19", "철수", 3000, "식비", "점심"
            ),
            self.make_expense(
                2, "2026-11-20", "영희", 5000, "카페", "커피"
            ),
        ])

        path = self.root / "roundtrip.csv"
        export_csv(
            store,
            path,
            start="2026-11-19",
            end="2026-11-19",
            category="식비",
        )

        self.assertEqual(
            roundtrip_check(
                store,
                path,
                start="2026-11-19",
                end="2026-11-19",
                category="식비",
            ),
            [],
        )

    def test_roundtrip_check_detects_modified_file_without_overwriting(self):
        store = self.make_store([
            self.make_expense(
                1, "2026-11-19", "철수", 1000, "식비", "점심"
            ),
        ])

        path = self.root / "roundtrip.csv"
        export_csv(store, path)

        # 내보낸 CSV의 금액을 직접 수정한다.
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            headers = reader.fieldnames

        rows[0]["amount"] = "9999"

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        result = roundtrip_check(store, path)

        # 수정된 CSV를 발견해야 한다.
        self.assertEqual(result, [1])

        # 검사 과정에서 파일이 덮어쓰여서는 안 된다.
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            checked_rows = list(csv.DictReader(f))

        self.assertEqual(checked_rows[0]["amount"], "9999")

    def test_roundtrip_check_returns_numeric_sorted_ids(self):
        store = self.make_store([
            self.make_expense(
                2, "2026-11-19", "철수", 2000, "식비", "2번"
            ),
            self.make_expense(
                10, "2026-11-20", "영희", 10000, "카페", "10번"
            ),
        ])

        path = self.root / "roundtrip.csv"
        export_csv(store, path)

        # 두 지출의 금액을 모두 바꾸어 불일치를 만든다.
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            headers = reader.fieldnames

        rows[0]["amount"] = "2222"
        rows[1]["amount"] = "10100"

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        self.assertEqual(roundtrip_check(store, path), [2, 10])

    def test_roundtrip_check_detects_duplicate_ids(self):
        store = self.make_store([
            self.make_expense(
                1, "2026-11-19", "철수", 3000, "식비", "점심"
            ),
        ])

        path = self.root / "roundtrip.csv"
        export_csv(store, path)

        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            headers = reader.fieldnames

        rows.append(rows[0].copy())

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        self.assertEqual(roundtrip_check(store, path), [1])

    def test_roundtrip_check_missing_required_header_raises_value_error(self):
        store = self.make_store([
            self.make_expense(
                1, "2026-11-19", "철수", 3000, "식비", "점심"
            ),
        ])

        path = self.root / "roundtrip.csv"
        path.write_text(
            "id,date,payer,amount,members,weights,category\n"
            "1,2026-11-19,철수,3000,철수;영희,,식비\n",
            encoding="utf-8-sig",
        )

        with self.assertRaises(ValueError):
            roundtrip_check(store, path)

    def test_roundtrip_check_non_numeric_id_raises_value_error(self):
        store = self.make_store([
            self.make_expense(
                1, "2026-11-19", "철수", 3000, "식비", "점심"
            ),
        ])

        path = self.root / "roundtrip.csv"
        export_csv(store, path)

        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            headers = reader.fieldnames

        rows[0]["id"] = "abc"

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        with self.assertRaises(ValueError):
            roundtrip_check(store, path)


if __name__ == "__main__":
    unittest.main()
