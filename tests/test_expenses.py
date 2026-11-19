"""지출 기본 기능의 잠금, 수정 이력, 삭제 표시를 확인한다."""

from helpers import NAMES, StoreCase
from moim.features import expenses


class ExpenseTests(StoreCase):
    def test_edit_preserves_weights_unless_explicitly_cleared(self):
        weights = {name: 1 for name in NAMES}
        expense, warnings = expenses.add_expense(
            self.store, "2026-11-12", NAMES[0], 3000, NAMES, weights=weights,
        )
        self.assertIsInstance(warnings, list)
        with self.assertRaisesRegex(ValueError, "비율"):
            expenses.edit_expense(self.store, expense["id"], members=NAMES[:2])
        self.assertEqual(expense["members"], NAMES)
        self.assertEqual(len(self.store.data["history"]), 1)

        expenses.edit_expense(
            self.store, expense["id"], members=NAMES[:2], weights=None, amount="4,000원",
        )
        entry = self.store.data["history"][-1]
        self.assertEqual(entry["action"], "edit")
        self.assertEqual(entry["before"]["weights"], weights)
        self.assertEqual(entry["after"]["members"], NAMES[:2])
        self.assertIsNone(entry["after"]["weights"])
        self.assertEqual(expense["amount"], 4000)

    def test_edit_and_delete_check_locked_dates(self):
        locked, _ = expenses.add_expense(self.store, "2026-11-12", NAMES[0], 3000, NAMES)
        unlocked, _ = expenses.add_expense(self.store, "2026-12-01", NAMES[0], 3000, NAMES)
        self.store.data["locks"].append({"start": "2026-11-01", "end": "2026-11-30"})

        with self.assertRaisesRegex(ValueError, "확정"):
            expenses.edit_expense(self.store, locked["id"], date="2026-12-01")
        with self.assertRaisesRegex(ValueError, "확정"):
            expenses.edit_expense(self.store, unlocked["id"], date="2026-11-30")
        with self.assertRaisesRegex(ValueError, "확정"):
            expenses.delete_expense(self.store, locked["id"])
        self.assertEqual(len(self.store.data["history"]), 2)
        self.assertEqual(locked["date"], "2026-11-12")
        self.assertEqual(unlocked["date"], "2026-12-01")
        self.assertFalse(locked["deleted"])

    def test_delete_keeps_old_expense_and_records_history(self):
        expense = {"id": 1, "date": "2026-11-12", "amount": 3000}
        self.store.data["expenses"].append(expense)
        self.assertEqual(expenses.list_expenses(self.store), [expense])

        expenses.delete_expense(self.store, "1")
        self.assertEqual(expenses.list_expenses(self.store), [])
        self.assertEqual(expenses.list_expenses(self.store, include_deleted=True), [expense])
        self.assertTrue(self.store.get_expense(1)["deleted"])
        entry = self.store.data["history"][-1]
        self.assertEqual(entry["action"], "delete")
        self.assertFalse(entry["before"].get("deleted", False))
        self.assertTrue(entry["after"]["deleted"])
