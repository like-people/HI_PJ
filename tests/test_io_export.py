"""기능 6: JSON 내보내기(export_json)와 `io export`·`io verify` 명령 테스트."""

import csv
import json
import unittest
from unittest.mock import patch

from helpers import NAMES, StoreCase
from moim.cli import main
from moim.common.store import Store
from moim.features.transfer_io import export_json, file_total, verify_export

KIM, LEE, PARK = NAMES


class ExportJsonCase(StoreCase):
    def setUp(self):
        super().setUp()
        rows = [
            (1, "2026-10-31", KIM, 5000, NAMES, None, "식비", "10월", False),
            (2, "2026-11-10", LEE, 10001, NAMES, {KIM: 2, LEE: 1, PARK: 1}, "식비", "회의, 점심", False),
            (3, "2026-11-11", KIM, 3000, [KIM, LEE], None, None, "", False),
            (4, "2026-11-12", PARK, 7000, NAMES, None, "교통", "택시", True),
        ]
        for eid, day, payer, amount, members, weights, category, memo, deleted in rows:
            self.store.data["expenses"].append({
                "id": eid, "date": day, "payer": payer, "amount": amount, "members": list(members),
                "weights": weights, "category": category, "memo": memo, "deleted": deleted,
            })

    def read_json(self, path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)


class ExportJson(ExportJsonCase):
    def test_format_follows_spec(self):
        path = self.path("all.json")
        self.assertEqual(export_json(self.store, path), (3, 18001))
        data = self.read_json(path)
        self.assertEqual(list(data), ["expenses"])
        self.assertEqual([e["id"] for e in data["expenses"]], [1, 2, 3])  # 삭제한 4번 제외
        self.assertEqual(data["expenses"][1], {
            "id": 2, "date": "2026-11-10", "payer": LEE, "amount": 10001, "members": NAMES,
            "weights": {KIM: 2, LEE: 1, PARK: 1}, "category": "식비", "memo": "회의, 점심",
        })
        self.assertEqual((data["expenses"][2]["weights"], data["expenses"][2]["category"]), (None, None))
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("회의, 점심", text)  # 한글을 그대로 쓴다
        self.assertIn('\n  "expenses"', text)  # 들여쓰기 2칸

    def test_period_and_category(self):
        path = self.path("food.json")
        self.assertEqual(export_json(self.store, path, "2026-11-01", "2026-11-30", "식비"), (1, 10001))
        self.assertEqual([e["id"] for e in self.read_json(path)["expenses"]], [2])
        self.assertEqual(export_json(self.store, path, category="미분류"), (1, 3000))

    def test_file_total_and_verify_read_it(self):
        path = self.path("nov.json")
        export_json(self.store, path, "2026-11-01", "2026-11-30")
        self.assertEqual(file_total(path), (2, 13001))
        self.assertEqual(verify_export(self.store, path, "2026-11-01", "2026-11-30"), (True, 13001, 13001))

    def test_empty(self):
        path = self.path("none.json")
        self.assertEqual(export_json(self.store, path, "2027-01-01", "2027-01-31"), (0, 0))
        self.assertEqual(self.read_json(path), {"expenses": []})


class IoCommands(ExportJsonCase):
    def setUp(self):
        super().setUp()
        self.store.save()
        self.output = []

    def io(self, *args):
        self.output.clear()
        with patch.object(Store, "save", side_effect=AssertionError("조회·내보내기 중 저장")):
            return main(["--config", self.path("config.json"), "io", *args], self.output.append)

    def test_export_csv_and_json_by_extension(self):
        csv_path, json_path = self.path("out.csv"), self.path("out.json")
        self.assertEqual(self.io("export", csv_path, "--month", "2026-11"), 0)
        self.assertEqual(self.output, [f"내보냈습니다: {csv_path} (2건, 합계 13,001원)"])
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            self.assertEqual(len(list(csv.reader(f))), 3)
        self.assertEqual(self.io("export", json_path, "--category", "식비"), 0)
        self.assertEqual(self.output, [f"내보냈습니다: {json_path} (2건, 합계 15,001원)"])

    def test_verify(self):
        path = self.path("out.json")
        self.io("export", path, "--start", "2026-11-01", "--end", "2026-11-30")
        self.assertEqual(self.io("verify", path, "--month", "2026-11"), 0)
        self.assertEqual(self.output, ["파일 합계 13,001원, 기록 합계 13,001원 → 같습니다"])
        self.assertEqual(self.io("verify", path), 0)  # 기간 없이 전체 기록과 비교
        self.assertEqual(self.output, ["파일 합계 13,001원, 기록 합계 18,001원 → 다릅니다"])

    def test_errors(self):
        self.assertEqual(self.io("verify", self.path("none.csv")), 1)
        self.assertTrue(self.output[0].startswith("오류: "))
        self.assertEqual(self.io("export", self.path("x.csv"), "--start", "2026-11-01"), 1)
        self.assertEqual(self.output, ["오류: 기간을 지정하십시오(--month YYYY-MM 또는 --start, --end)"])


if __name__ == "__main__":
    unittest.main()
