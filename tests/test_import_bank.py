"""은행 CSV 가져오기 및 명령 저장 흐름 테스트. 담당: 기능 5(이정배)."""

import csv
from pathlib import Path

from helpers import NAMES, StoreCase
from moim.common import ledger
from moim.features.budget import BANK_COLUMNS, import_bank, record_payment

KIM, LEE, PARK = NAMES


class TestImportBank(StoreCase):
    def write_bank(self, rows, encoding="utf-8"):
        path = self.path("bank.csv")
        with open(path, "w", encoding=encoding, newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(BANK_COLUMNS)
            writer.writerows(rows)
        return path

    def test_cp949_reordered_columns_and_active_members(self):
        self.store.member(PARK)["left"] = "2026-11-02"
        path = Path(self.path("bank.csv"))
        with path.open("w", encoding="cp949", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(reversed(BANK_COLUMNS))
            writer.writerow(reversed(("2026.11.03", "19:42", "회의 후 저녁", "48,000", "", "-28000")))
            writer.writerow(reversed(("2026.11.01", "09:10", LEE, "", "20,000", "20000")))

        self.assertEqual(import_bank(self.store, path, KIM),
                         {"expenses": [1], "payments": 1, "duplicates": [], "errors": []})
        expense = self.store.data["expenses"][0]
        self.assertEqual((expense["date"], expense["payer"], expense["members"], expense["amount"]),
                         ("2026-11-03", KIM, [KIM, LEE], 48000))
        self.assertEqual(expense["memo"], "회의 후 저녁")
        self.assertEqual(self.store.data["history"][0]["eid"], expense["id"])
        self.assertNotIn("source", expense)
        self.assertEqual(self.store.data["payments"][0], {
            "date": "2026-11-01", "member": LEE, "amount": 20000, "memo": "", "source": "bank",
        })

    def test_existing_manual_records_and_deleted_expense(self):
        record_payment(self.store, "2026-11-03", LEE, 1000)
        ledger.insert(self.store, "2026-11-03", LEE, 2000, [LEE], memo="간식")
        deleted = ledger.insert(self.store, "2026-11-03", KIM, 500, [KIM], memo="교통")
        deleted["deleted"] = True
        path = self.write_bank([
            ("2026.11.03", "11:00", LEE, "", "1,000", "1000"),
            ("2026.11.03", "12:00", "간식", "2,000", "", "-1000"),
            ("2026.11.03", "13:00", "교통", "500", "", "-1500"),
        ])
        self.assertEqual(import_bank(self.store, path, KIM),
                         {"expenses": [3], "payments": 0, "duplicates": [2, 3], "errors": []})

    def test_file_duplicates_and_reimport(self):
        row = ("2026.11.03", "11:00", LEE, "", "1000", "1000")
        later = ("2026.11.03", "12:00", LEE, "", "1000", "2000")
        path = self.write_bank([row, row, later])
        self.assertEqual(import_bank(self.store, path, KIM),
                         {"expenses": [], "payments": 2, "duplicates": [3], "errors": []})
        self.assertEqual(import_bank(self.store, path, KIM),
                         {"expenses": [], "payments": 0, "duplicates": [2, 3, 4], "errors": []})

    def test_row_errors_keep_file_line_numbers_and_import_valid_rows(self):
        path = self.write_bank([
            ("2026.11.03", "11:00", "모르는\n입금자", "", "1000", "1000"),
            (),
            ("2026.11.03", "11:10", "양쪽", "10", "10", "1000"),
            ("2026.11.03", "11:20", "빈 금액", "0", "", "1000"),
            ("2026.11.03", "11:30", LEE, "", "Infinity", "1000"),
            ("2026.11.03", "11:40", LEE, "", "-100", "1000"),
            ("2026.02.30", "11:50", LEE, "", "1000", "2000"),
            ("2026.11.03", "12:00", LEE, "", "1000", "3000"),
        ])
        result = import_bank(self.store, path, KIM)
        self.assertEqual([line for line, _ in result["errors"]], [2, 5, 6, 7, 8, 9])
        self.assertEqual(result["payments"], 1)
        self.assertEqual(len(self.store.data["payments"]), 1)

    def test_ledger_rejects_locked_dates_and_inactive_treasurer(self):
        self.store.data["locks"].append({"start": "2026-11-01", "end": "2026-11-03"})
        self.store.member(KIM)["left"] = "2026-11-03"
        path = self.write_bank([
            ("2026.11.03", "11:00", "간식", "1000", "", "-1000"),
            ("2026.11.04", "11:00", "식사", "2000", "", "-3000"),
        ])
        result = import_bank(self.store, path, KIM)
        self.assertEqual(result["expenses"], [])
        self.assertIn("확정", result["errors"][0][1])
        self.assertIn("활동 중인 회원", result["errors"][1][1])
        self.assertEqual(self.store.data["history"], [])

