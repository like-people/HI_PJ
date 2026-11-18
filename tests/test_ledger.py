"""지출 공통 함수의 검증, 등록, 이력 기록을 확인한다."""

import os
from datetime import date

from helpers import NAMES, StoreCase
from moim.common import ledger


class LedgerTests(StoreCase):
    DAY = "2026-11-12"

    def test_normalizes_date_and_amount_without_modifying_store(self):
        result = ledger.validate(
            self.store, date(2026, 11, 12), NAMES[0], "1,234.5원",
            NAMES[1:], {NAMES[1]: 2, NAMES[2]: 1},
        )
        self.assertEqual(result, (self.DAY, 1235))
        self.assertEqual(self.store.data["expenses"], [])
        self.assertEqual(self.store.data["history"], [])
        self.assertEqual(self.store.data["next_id"], 1)

    def test_rejects_invalid_date_and_amount(self):
        with self.assertRaisesRegex(ValueError, "날짜"):
            ledger.validate(self.store, "2026-02-30", NAMES[0], 1000, NAMES)
        for amount in (0, -1, "0.4", "NaN", "Infinity"):
            with self.subTest(amount=amount), self.assertRaisesRegex(ValueError, "금액"):
                ledger.validate(self.store, self.DAY, NAMES[0], amount, NAMES)

    def test_rejects_missing_or_duplicate_participants(self):
        for members in ([], [NAMES[0], NAMES[0]]):
            with self.subTest(members=members), self.assertRaisesRegex(ValueError, "참여자"):
                ledger.validate(self.store, self.DAY, NAMES[0], 1000, members)

    def test_checks_membership_and_includes_leave_day(self):
        self.store.member(NAMES[1])["left"] = self.DAY
        self.assertEqual(
            ledger.validate(self.store, self.DAY, NAMES[0], 1000, [NAMES[1]]),
            (self.DAY, 1000),
        )
        with self.assertRaisesRegex(ValueError, "참여자"):
            ledger.validate(self.store, "2026-11-13", NAMES[0], 1000, [NAMES[1]])
        with self.assertRaisesRegex(ValueError, "낸 사람"):
            ledger.validate(self.store, self.DAY, "없는사람", 1000, NAMES)
        with self.assertRaisesRegex(ValueError, "참여자"):
            ledger.validate(self.store, self.DAY, NAMES[0], 1000, ["없는사람"])

    def test_rejects_invalid_weights(self):
        members = NAMES[:2]
        for weights in ({}, {NAMES[0]: 1}, {NAMES[0]: True, NAMES[1]: 1},
                        {NAMES[0]: 1.0, NAMES[1]: 1}, {NAMES[0]: 0, NAMES[1]: 1}):
            with self.subTest(weights=weights), self.assertRaisesRegex(ValueError, "비율"):
                ledger.validate(self.store, self.DAY, NAMES[0], 1000, members, weights)

    def test_locked_dates_leave_store_unchanged(self):
        self.store.data["locks"].append({"start": "2026-11-01", "end": "2026-11-30"})
        for day in ("2026-11-01", "2026-11-30"):
            with self.subTest(day=day), self.assertRaisesRegex(ValueError, "확정"):
                ledger.insert(self.store, day, NAMES[0], 1000, NAMES)
        self.assertEqual(self.store.data["next_id"], 1)
        self.assertEqual(self.store.data["expenses"], [])
        self.assertEqual(self.store.data["history"], [])

    def test_insert_stores_defaults_and_allocates_ids(self):
        first = ledger.insert(self.store, self.DAY, NAMES[0], "1,000원", NAMES)
        second = ledger.insert(self.store, self.DAY, NAMES[0], 1000, NAMES)
        self.assertEqual(first, {
            "id": 1, "date": self.DAY, "payer": NAMES[0], "amount": 1000,
            "members": NAMES, "memo": "", "weights": None, "category": None,
            "recurring_id": None, "deleted": False,
        })
        self.assertEqual(second["id"], 2)
        self.assertIs(self.store.get_expense(1), first)
        self.assertEqual(self.store.data["history"][0]["action"], "add")
        self.assertFalse(os.path.exists(self.store.path))

    def test_insert_preserves_optional_fields_and_history_snapshot(self):
        members = NAMES[:2]
        weights = {members[0]: 2, members[1]: 1}
        expense = ledger.insert(
            self.store, self.DAY, NAMES[0], 3000, members, memo="회의",
            weights=weights, category="식비", recurring_id=7, action="recurring",
        )
        entry = self.store.data["history"][0]
        self.assertEqual((entry["action"], entry["eid"], entry["before"]),
                         ("recurring", expense["id"], None))
        self.assertEqual(entry["after"], expense)
        self.assertEqual((expense["memo"], expense["category"], expense["recurring_id"]),
                         ("회의", "식비", 7))

        members.clear()
        weights.clear()
        self.assertEqual(expense["members"], NAMES[:2])
        self.assertEqual(expense["weights"], {NAMES[0]: 2, NAMES[1]: 1})
        expense["amount"] = 4000
        self.assertEqual(entry["after"]["amount"], 3000)
