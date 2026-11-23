"""기능 1: 파일로 여러 줄 입력(add_from_file)과 `exp import-lines` 명령 테스트."""

import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from helpers import NAMES, StoreCase
from moim.cli import main
from moim.common.store import Store
from moim.features import expenses

KIM, LEE, PARK = NAMES
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AddFromFile(StoreCase):
    def write(self, text, encoding="utf-8"):
        path = self.path("lines.csv")
        with open(path, "w", encoding=encoding, newline="") as f:
            f.write(text)
        return path

    def test_adds_lines_and_skips_comments_and_blanks(self):
        path = self.write(f"# 11월 지출\n\n2026-11-12,{KIM},\"36,000\",{KIM};{LEE},회의 후 저녁\n"
                          f"2026-11-13,{LEE},9000,{LEE};{PARK}\n")
        added, errors = expenses.add_from_file(self.store, path)
        self.assertEqual((added, errors), ([1, 2], []))
        first, second = self.store.get_expense(1), self.store.get_expense(2)
        self.assertEqual((first["amount"], first["members"], first["memo"]), (36000, [KIM, LEE], "회의 후 저녁"))
        self.assertEqual((second["payer"], second["memo"]), (LEE, ""))
        self.assertEqual([h["action"] for h in self.store.data["history"]], ["add", "add"])

    def test_errors_report_real_line_numbers_and_continue(self):
        self.store.data["locks"].append({"start": "2026-10-01", "end": "2026-10-31"})
        path = self.write("\n".join([
            f"2026-11-12,{KIM},3000,{KIM}",          # 1 정상
            "# 설명",                                  # 2 건너뜀
            f"2026-11-12,{KIM},3000",                 # 3 칸 부족
            f"2026-02-30,{KIM},3000,{KIM}",           # 4 없는 날짜
            f"2026-11-12,{KIM},0,{KIM}",              # 5 금액
            f"2026-11-12,없는사람,3000,{KIM}",          # 6 명부
            f"2026-10-12,{KIM},3000,{KIM}",           # 7 확정 기간
            "",                                        # 8 빈 줄
            f"2026-11-13,{LEE},1000,{LEE},메모,쉼표",   # 9 정상(메모에 쉼표)
        ]) + "\n")
        added, errors = expenses.add_from_file(self.store, path)
        self.assertEqual(added, [1, 2])
        self.assertEqual([no for no, _ in errors], [3, 4, 5, 6, 7])
        self.assertIn("확정", errors[-1][1])
        self.assertEqual(self.store.get_expense(2)["memo"], "메모,쉼표")

    def test_cp949_and_bom_files(self):
        for encoding in ("cp949", "utf-8-sig"):
            with self.subTest(encoding=encoding):
                path = self.write(f"2026-11-12,{KIM},3000,{KIM};{LEE},점심\n", encoding)
                added, errors = expenses.add_from_file(self.store, path)
                self.assertEqual((len(added), errors), (1, []))
                self.assertEqual(self.store.get_expense(added[0])["memo"], "점심")

    def test_gen_data_expenses_file(self):
        out = self.path("sample")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "gen_data.py"), out, "--count", "15"],
                       check=True, capture_output=True)
        expenses.load_members_file(self.store, os.path.join(out, "members.txt"))
        added, errors = expenses.add_from_file(self.store, os.path.join(out, "expenses.csv"))
        self.assertEqual((len(added), errors), (15, []))

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            expenses.add_from_file(self.store, self.path("none.csv"))


class ExpImportLinesCommand(StoreCase):
    def setUp(self):
        super().setUp()
        self.store.save()
        self.output = []

    def exp(self, *args):
        self.output.clear()
        return main(["--config", self.path("config.json"), "exp", *args], self.output.append)

    def test_import_is_saved_and_errors_listed(self):
        path = self.path("lines.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"2026-11-12,{KIM},3000,{KIM};{LEE},점심\n2026-11-12,{KIM},0,{KIM}\n")
        self.assertEqual(self.exp("import-lines", path), 0)
        self.assertEqual(self.output[0], "추가 1건, 오류 1줄")
        self.assertTrue(self.output[1].startswith("2번째 줄: 금액"))
        self.assertEqual(len(Store(self.store.path).load().data["expenses"]), 1)

    def test_only_errors_does_not_save(self):
        path = self.path("bad.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write("잘못된 줄\n")
        with patch.object(Store, "save", side_effect=AssertionError("추가 없이 저장")):
            self.assertEqual(self.exp("import-lines", path), 0)
        self.assertEqual(self.output[0], "추가 0건, 오류 1줄")

    def test_missing_file_is_error(self):
        self.assertEqual(self.exp("import-lines", self.path("none.csv")), 1)
        self.assertTrue(self.output[0].startswith("오류: "))


if __name__ == "__main__":
    unittest.main()
