"""기능 1: 수정·삭제 이력(history)과 `exp history` 명령 테스트."""

import unittest
from unittest.mock import patch

from helpers import NAMES, StoreCase
from moim.cli import main
from moim.common.store import Store
from moim.features import expenses

KIM, LEE, PARK = NAMES


class History(StoreCase):
    def setUp(self):
        super().setUp()
        self.a = expenses.add_expense(self.store, "2026-11-12", KIM, 3000, NAMES)[0]
        self.b = expenses.add_expense(self.store, "2026-11-13", LEE, 6000, NAMES)[0]
        expenses.edit_expense(self.store, self.a["id"], amount=4500)
        expenses.delete_expense(self.store, self.b["id"])

    def test_all_in_recorded_order(self):
        entries = expenses.history(self.store)
        self.assertEqual([(h["action"], h["eid"]) for h in entries],
                         [("add", 1), ("add", 2), ("edit", 1), ("delete", 2)])
        self.assertEqual(set(entries[0]), {"at", "action", "eid", "before", "after"})

    def test_filter_by_id(self):
        self.assertEqual([h["action"] for h in expenses.history(self.store, self.a["id"])], ["add", "edit"])
        self.assertEqual([h["action"] for h in expenses.history(self.store, "2")], ["add", "delete"])
        self.assertEqual(expenses.history(self.store, 99), [])

    def test_returns_copies(self):
        entries = expenses.history(self.store)
        entries[2]["after"]["amount"] = 1
        entries.clear()
        self.assertEqual(self.store.data["history"][2]["after"]["amount"], 4500)

    def test_old_data_without_history(self):
        del self.store.data["history"]
        self.assertEqual(expenses.history(self.store), [])


class ExpHistoryCommand(StoreCase):
    def setUp(self):
        super().setUp()
        e = expenses.add_expense(self.store, "2026-11-12", KIM, 3000, NAMES, memo="저녁")[0]
        expenses.edit_expense(self.store, e["id"], amount=4500, members=[KIM, LEE])
        expenses.delete_expense(self.store, e["id"])
        self.store.save()
        self.output = []

    def exp(self, *args):
        self.output.clear()
        with patch.object(Store, "save", side_effect=AssertionError("조회 중 저장")):
            return main(["--config", self.path("config.json"), "exp", *args], self.output.append)

    def test_table_shows_actions_and_changes(self):
        self.assertEqual(self.exp("history", "1"), 0)
        lines = self.output[0].splitlines()
        self.assertEqual(lines[0].split(), ["시각", "작업", "번호", "내용"])
        self.assertEqual(len(lines), 5)
        self.assertIn(f"추가  1     2026-11-12 {KIM} 3,000 {KIM};{LEE};{PARK}", lines[2])
        self.assertIn(f"수정  1     금액 3,000→4,500, 참여자 {KIM};{LEE};{PARK}→{KIM};{LEE}", lines[3])
        self.assertIn("삭제  1", lines[4])

    def test_empty(self):
        self.assertEqual(self.exp("history", "99"), 0)
        self.assertEqual(self.output, ["이력이 없습니다."])


if __name__ == "__main__":
    unittest.main()
