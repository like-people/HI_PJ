"""명령 묶음 cat(commands/categorize.py) 테스트.

moim.cli.main 으로 명령을 직접 실행해 화면 출력, 종료 코드, 자료 파일의 변화를 확인한다.
실행: python -m unittest discover -s tests -v
"""

import json
import unittest

from helpers import NAMES, StoreCase

from moim.cli import main
from moim.common.store import Store


class CatCommandCase(StoreCase):
    def setUp(self):
        super().setUp()
        self.config = self.path("config.json")
        with open(self.config, "w", encoding="utf-8") as f:
            json.dump({}, f)
        self.put(1, 12000, "팀 저녁")
        self.put(2, 3000, "현수막")
        self.store.save()

    def put(self, eid, amount, memo):
        self.store.data["expenses"].append(
            {"id": eid, "date": "2026-11-10", "payer": NAMES[0], "amount": amount,
             "members": list(NAMES), "category": None, "memo": memo})

    def cat(self, *args):
        output = []
        code = main(["--config", self.config, "cat", *args], output.append)
        return code, output

    def expense(self, eid):
        store = Store(self.path("data.json")).load()
        return next(e for e in store.data["expenses"] if e["id"] == eid)

    def data_text(self):
        with open(self.path("data.json"), encoding="utf-8") as f:
            return f.read()


class RuleCommands(CatCommandCase):
    def test_add_rule_then_listed(self):
        code, output = self.cat("add-rule", "식비", "--keywords", "저녁;회식")
        self.assertEqual((code, output), (0, ["규칙을 추가했습니다: 식비"]))
        code, output = self.cat("rules")
        self.assertEqual(code, 0)
        self.assertEqual(len(output), 1)
        self.assertIn("1. 식비", output[0])
        self.assertIn("저녁;회식", output[0])

    def test_rules_empty(self):
        self.assertEqual(self.cat("rules"), (0, ["규칙이 없습니다"]))

    def test_remove_rule_disappears_from_list(self):
        self.cat("add-rule", "식비", "--keywords", "저녁")
        self.cat("add-rule", "소품", "--keywords", "현수막")
        code, output = self.cat("remove-rule", "1")
        self.assertEqual((code, output), (0, ["규칙을 삭제했습니다: 식비"]))
        code, output = self.cat("rules")
        self.assertEqual(len(output), 1)
        self.assertIn("1. 소품", output[0])

    def test_remove_rule_unknown_number_is_error(self):
        self.assertEqual(self.cat("remove-rule", "9"), (1, ["오류: 없는 규칙 번호입니다: 9"]))

    def test_overlaps_reports_shared_keyword(self):
        self.cat("add-rule", "식비", "--keywords", "저녁")
        self.cat("add-rule", "회식", "--keywords", "저녁;술")
        code, output = self.cat("overlaps")
        self.assertEqual(code, 0)
        self.assertEqual(output, ["규칙 1번과 2번이 키워드 '저녁'를 함께 씁니다"])


class ApplyCommands(CatCommandCase):
    def setUp(self):
        super().setUp()
        self.cat("add-rule", "식비", "--keywords", "저녁")

    def test_apply_preview_does_not_change_data(self):
        before = self.data_text()
        code, output = self.cat("apply", "--preview")
        self.assertEqual(code, 0)
        self.assertEqual(output[-1], "1건 바뀔 예정")
        self.assertEqual(self.data_text(), before)
        self.assertIsNone(self.expense(1)["category"])

    def test_apply_changes_and_saves(self):
        code, output = self.cat("apply")
        self.assertEqual(code, 0)
        self.assertEqual(output[-1], "1건 바꿨습니다")
        self.assertEqual(self.expense(1)["category"], "식비")
        self.assertIsNone(self.expense(2)["category"])


class SetAndListCommands(CatCommandCase):
    def test_set_fixes_category_and_apply_keeps_it(self):
        self.cat("add-rule", "식비", "--keywords", "현수막")
        code, output = self.cat("set", "2", "장소")
        self.assertEqual((code, output), (0, ["2번 분류를 장소(으)로 정했습니다"]))
        self.assertEqual(self.expense(2)["category"], "장소")
        self.assertTrue(self.expense(2)["category_fixed"])
        self.cat("apply")
        self.assertEqual(self.expense(2)["category"], "장소")

    def test_unfix_allows_rules_again(self):
        self.cat("add-rule", "식비", "--keywords", "현수막")
        self.cat("set", "2", "장소")
        code, output = self.cat("unfix", "2")
        self.assertEqual((code, output), (0, ["2번 분류 고정을 풀었습니다"]))
        self.cat("apply")
        self.assertEqual(self.expense(2)["category"], "식비")

    def test_set_unknown_expense_is_error(self):
        code, output = self.cat("set", "99", "장소")
        self.assertEqual(code, 1)
        self.assertTrue(output[0].startswith("오류: "))

    def test_uncategorized_lists_expenses_without_category(self):
        code, output = self.cat("uncategorized")
        self.assertEqual(code, 0)
        self.assertEqual(output, ["1번 2026-11-10 김민수 12,000원 팀 저녁",
                                  "2번 2026-11-10 김민수 3,000원 현수막"])

    def test_summary_by_month(self):
        self.cat("set", "1", "식비")
        code, output = self.cat("summary", "--month", "2026-11")
        self.assertEqual(code, 0)
        self.assertEqual(output, ["식비 1건 12,000원", "미분류 1건 3,000원"])


if __name__ == "__main__":
    unittest.main()