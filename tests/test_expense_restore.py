"""기능 1: 삭제한 지출 되살리기(restore_expense)와 `exp restore` 명령 테스트."""

import unittest
from unittest.mock import patch

from helpers import NAMES, StoreCase
from moim.cli import main
from moim.common.store import Store
from moim.features import expenses

KIM, LEE, PARK = NAMES


class RestoreExpense(StoreCase):
    def add(self, day="2026-11-12", members=NAMES):
        return expenses.add_expense(self.store, day, KIM, 3000, list(members))[0]

    def test_restore_shows_in_list_and_records_history(self):
        e = self.add()
        expenses.delete_expense(self.store, e["id"])
        self.assertIs(expenses.restore_expense(self.store, e["id"]), e)
        self.assertFalse(e["deleted"])
        self.assertEqual(expenses.list_expenses(self.store), [e])
        entry = self.store.data["history"][-1]
        self.assertEqual((entry["action"], entry["eid"]), ("restore", e["id"]))
        self.assertTrue(entry["before"]["deleted"])
        self.assertFalse(entry["after"]["deleted"])

    def test_not_deleted_is_unchanged(self):
        e = self.add()
        count = len(self.store.data["history"])
        self.assertFalse(expenses.restore_expense(self.store, str(e["id"]))["deleted"])
        self.assertEqual(len(self.store.data["history"]), count)

    def test_locked_date_rejected(self):
        e = self.add()
        expenses.delete_expense(self.store, e["id"])
        self.store.data["locks"].append({"start": "2026-11-01", "end": "2026-11-30"})
        with self.assertRaisesRegex(ValueError, "확정"):
            expenses.restore_expense(self.store, e["id"])
        self.assertTrue(e["deleted"])

    def test_member_who_left_blocks_restore(self):
        e = self.add(day="2026-11-20", members=[KIM, LEE])
        expenses.delete_expense(self.store, e["id"])
        self.store.member(LEE)["left"] = "2026-11-15"
        count = len(self.store.data["history"])
        with self.assertRaisesRegex(ValueError, "되살릴 수 없습니다.*참여자"):
            expenses.restore_expense(self.store, e["id"])
        self.assertTrue(e["deleted"])
        self.assertEqual(len(self.store.data["history"]), count)

    def test_unknown_id(self):
        with self.assertRaises(ValueError):
            expenses.restore_expense(self.store, 99)


class ExpRestoreCommand(StoreCase):
    def setUp(self):
        super().setUp()
        e = expenses.add_expense(self.store, "2026-11-12", KIM, 3000, NAMES)[0]
        expenses.delete_expense(self.store, e["id"])
        self.store.save()
        self.output = []

    def exp(self, *args):
        self.output.clear()
        return main(["--config", self.path("config.json"), "exp", *args], self.output.append)

    def test_restore_is_saved(self):
        self.assertEqual(self.exp("restore", "1"), 0)
        self.assertEqual(self.output, ["1번 지출을 되살렸습니다."])
        self.assertFalse(Store(self.store.path).load().get_expense(1)["deleted"])

    def test_restore_twice_does_not_save(self):
        self.exp("restore", "1")
        with patch.object(Store, "save", side_effect=AssertionError("바뀐 것 없이 저장")):
            self.assertEqual(self.exp("restore", "1"), 0)
        self.assertEqual(self.output, ["1번 지출은 삭제되지 않았습니다."])

    def test_unknown_id_is_error(self):
        self.assertEqual(self.exp("restore", "99"), 1)
        self.assertTrue(self.output[0].startswith("오류: "))


if __name__ == "__main__":
    unittest.main()
