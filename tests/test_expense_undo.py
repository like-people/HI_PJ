"""기능 1: 최근 수정 되돌리기(undo_last_edit)와 `exp undo` 명령 테스트."""

import unittest
from unittest.mock import patch

from helpers import NAMES, StoreCase
from moim.cli import main
from moim.common.store import Store
from moim.features import expenses, settle

KIM, LEE, PARK = NAMES


class UndoLastEdit(StoreCase):
    def setUp(self):
        super().setUp()
        self.e = expenses.add_expense(self.store, "2026-11-12", KIM, 3000, NAMES, memo="저녁")[0]

    def test_undo_restores_before_values_and_records_history(self):
        expenses.edit_expense(self.store, self.e["id"], amount=4500, memo="회식")
        expenses.undo_last_edit(self.store, self.e["id"])
        self.assertEqual((self.e["amount"], self.e["memo"]), (3000, "저녁"))
        entry = self.store.data["history"][-1]
        self.assertEqual((entry["action"], entry["eid"]), ("undo", self.e["id"]))
        self.assertEqual(entry["before"]["amount"], 4500)
        self.assertEqual(entry["after"]["amount"], 3000)

    def test_repeated_undo_steps_back_one_edit_at_a_time(self):
        expenses.edit_expense(self.store, self.e["id"], amount=4000)
        expenses.edit_expense(self.store, self.e["id"], amount=5000)
        expenses.undo_last_edit(self.store, self.e["id"])
        self.assertEqual(self.e["amount"], 4000)
        expenses.undo_last_edit(self.store, self.e["id"])
        self.assertEqual(self.e["amount"], 3000)
        with self.assertRaisesRegex(ValueError, "되돌릴 수정이 없습니다"):
            expenses.undo_last_edit(self.store, self.e["id"])

    def test_edit_after_undo_is_undone_first(self):
        expenses.edit_expense(self.store, self.e["id"], amount=4000)
        expenses.undo_last_edit(self.store, self.e["id"])
        expenses.edit_expense(self.store, self.e["id"], memo="회식")
        expenses.undo_last_edit(self.store, self.e["id"])
        self.assertEqual((self.e["amount"], self.e["memo"]), (3000, "저녁"))

    def test_only_fields_changed_by_that_edit(self):
        expenses.edit_expense(self.store, self.e["id"], amount=6000)
        settle.exclude_member(self.store, self.e["id"], PARK)
        expenses.undo_last_edit(self.store, self.e["id"])
        self.assertEqual((self.e["amount"], self.e["members"]), (3000, [KIM, LEE]))

    def test_weights_and_members_restored(self):
        expenses.edit_expense(self.store, self.e["id"], members=[KIM, LEE], weights={KIM: 2, LEE: 1})
        expenses.undo_last_edit(self.store, self.e["id"])
        self.assertEqual((self.e["members"], self.e["weights"]), (NAMES, None))

    def test_no_edit_or_deleted_rejected(self):
        with self.assertRaisesRegex(ValueError, "되돌릴 수정이 없습니다"):
            expenses.undo_last_edit(self.store, self.e["id"])
        expenses.edit_expense(self.store, self.e["id"], amount=4000)
        expenses.delete_expense(self.store, self.e["id"])
        with self.assertRaisesRegex(ValueError, "삭제"):
            expenses.undo_last_edit(self.store, self.e["id"])

    def test_locked_dates_rejected(self):
        expenses.edit_expense(self.store, self.e["id"], date="2026-12-01")
        self.store.data["locks"].append({"start": "2026-11-01", "end": "2026-11-30"})
        count = len(self.store.data["history"])
        with self.assertRaisesRegex(ValueError, "확정"):
            expenses.undo_last_edit(self.store, self.e["id"])   # 되돌리면 확정 기간(11/12)으로 옮겨짐
        self.assertEqual(self.e["date"], "2026-12-01")
        self.store.data["locks"].append({"start": "2026-12-01", "end": "2026-12-31"})
        with self.assertRaisesRegex(ValueError, "확정"):
            expenses.undo_last_edit(self.store, self.e["id"])   # 지금 날짜가 확정 기간
        self.assertEqual(len(self.store.data["history"]), count)


class ExpUndoCommand(StoreCase):
    def setUp(self):
        super().setUp()
        e = expenses.add_expense(self.store, "2026-11-12", KIM, 3000, NAMES)[0]
        expenses.edit_expense(self.store, e["id"], amount=4500)
        self.store.save()
        self.output = []

    def exp(self, *args):
        self.output.clear()
        return main(["--config", self.path("config.json"), "exp", *args], self.output.append)

    def test_undo_is_saved(self):
        self.assertEqual(self.exp("undo", "1"), 0)
        self.assertEqual(self.output, ["1번 지출의 최근 수정을 되돌렸습니다."])
        self.assertEqual(Store(self.store.path).load().get_expense(1)["amount"], 3000)

    def test_nothing_to_undo_is_error_without_saving(self):
        self.exp("undo", "1")
        with patch.object(Store, "save", side_effect=AssertionError("오류 뒤 저장")):
            self.assertEqual(self.exp("undo", "1"), 1)
        self.assertEqual(self.output, ["오류: 1번 지출에 되돌릴 수정이 없습니다"])


if __name__ == "__main__":
    unittest.main()
