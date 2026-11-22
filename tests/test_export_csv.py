import csv

from helpers import StoreCase, NAMES
from moim.features.transfer_io import export_csv


class ExportCsvTests(StoreCase):
    def add_expense(
        self, eid, date, payer, amount, members,
        weights=None, category=None, memo="",
        deleted=False,
    ):
        self.store.data["expenses"].append({
            "id": eid,
            "date": date,
            "payer": payer,
            "amount": amount,
            "members": list(members),
            "weights": weights,
            "category": category,
            "memo": memo,
            "deleted": deleted,
        })

    def read_rows(self, path):
        with open(path, encoding="utf-8-sig", newline="") as f:
            return list(csv.reader(f))

    def test_exports_header_and_rows(self):
        kim, lee, park = NAMES
        self.add_expense(
            1, "2026-11-10", lee, 10001, NAMES,
            weights={kim: 2, lee: 1, park: 1},
            category="식비",
            memo="회의, 점심",
        )
        self.add_expense(2, "2026-11-11", kim, 3000, NAMES)

        path = self.path("expenses.csv")
        result = export_csv(self.store, path)

        self.assertEqual(result, (2, 13001))
        rows = self.read_rows(path)

        self.assertEqual(rows[0], [
            "id", "date", "payer", "amount",
            "members", "weights", "category", "memo",
        ])
        self.assertEqual(rows[1], [
            "1", "2026-11-10", lee, "10001",
            ";".join(NAMES),
            f"{kim}:2;{lee}:1;{park}:1",
            "식비", "회의, 점심",
        ])
        self.assertEqual(rows[2], [
            "2", "2026-11-11", kim, "3000",
            ";".join(NAMES), "", "", "",
        ])

    def test_excludes_deleted_expenses(self):
        self.add_expense(
            1, "2026-11-10", NAMES[0], 1000, NAMES,
            deleted=True,
        )
        self.add_expense(
            2, "2026-11-11", NAMES[1], 2000, NAMES,
        )

        path = self.path("expenses.csv")
        self.assertEqual(export_csv(self.store, path), (1, 2000))
        self.assertEqual(len(self.read_rows(path)), 2)

    def test_date_and_category_filters(self):
        self.add_expense(
            1, "2026-11-09", NAMES[0], 1000, NAMES,
            category="식비",
        )
        self.add_expense(
            2, "2026-11-10", NAMES[0], 2000, NAMES,
            category="교통",
        )
        self.add_expense(
            3, "2026-11-11", NAMES[0], 3000, NAMES,
            category=None,
        )
        self.add_expense(
            4, "2026-11-12", NAMES[0], 4000, NAMES,
            category="식비",
        )

        path = self.path("expenses.csv")
        result = export_csv(
            self.store, path,
            start="2026-11-10",
            end="2026-11-12",
            category="식비",
        )

        self.assertEqual(result, (1, 4000))
        rows = self.read_rows(path)
        self.assertEqual(rows[1][0], "4")

    def test_uncategorized_filter(self):
        self.add_expense(
            1, "2026-11-10", NAMES[0], 1000, NAMES,
            category=None,
        )
        self.add_expense(
            2, "2026-11-11", NAMES[0], 2000, NAMES,
            category="식비",
        )

        path = self.path("expenses.csv")
        result = export_csv(
            self.store, path, category="미분류",
        )

        self.assertEqual(result, (1, 1000))
        self.assertEqual(self.read_rows(path)[1][6], "")

    def test_explicit_uncategorized_and_missing_category(self):
        self.add_expense(
            1, "2026-11-10", NAMES[0], 1000, NAMES,
            category="미분류",
        )
        self.add_expense(
            2, "2026-11-11", NAMES[0], 2000, NAMES,
            category=None,
        )

        path = self.path("uncategorized.csv")
        result = export_csv(self.store, path)

        self.assertEqual(result, (2, 3000))

        rows = self.read_rows(path)
        self.assertEqual(rows[1][6], "미분류")
        self.assertEqual(rows[2][6], "")

    def test_empty_export_still_writes_header(self):
        path = self.path("empty.csv")

        self.assertEqual(export_csv(self.store, path), (0, 0))
        self.assertEqual(len(self.read_rows(path)), 1)

    def test_output_has_utf8_bom(self):
        path = self.path("bom.csv")
        export_csv(self.store, path)

        with open(path, "rb") as f:
            self.assertTrue(f.read().startswith(b"\xef\xbb\xbf"))
