import json
import tempfile
from pathlib import Path

from helpers import StoreCase, NAMES
from moim.features.transfer_io import merge


class MergeTests(StoreCase):
    def create_backup(self, data):
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            delete=False,
        )
        json.dump(data, temp_file, ensure_ascii=False)
        temp_file.close()

        path = Path(temp_file.name)
        self.addCleanup(path.unlink)
        return path

    def valid_expense(self, eid=100, payer=None, members=None):
        payer = payer or NAMES[0]
        members = members or [NAMES[0], NAMES[1]]

        return {
            "id": eid,
            "date": "2026-10-01",
            "payer": payer,
            "amount": 10000,
            "members": members,
            "memo": "병합 테스트",
            "weights": None,
            "category": None,
            "deleted": False,
        }

    def test_merge_adds_new_members_and_expenses(self):
        backup = self.create_backup({
            "members": [
                {
                    "name": "새회원",
                    "joined": "2026-09-01",
                    "left": None,
                },
            ],
            "expenses": [
                self.valid_expense(
                    payer="새회원",
                    members=["새회원"],
                ),
            ],
        })

        before = len(self.store.data["expenses"])

        added = merge(self.store, backup)

        self.assertEqual(added, 1)
        self.assertIn(
            "새회원",
            [member["name"] for member in self.store.data["members"]],
        )
        self.assertEqual(
            len(self.store.data["expenses"]),
            before + 1,
        )

    def test_merge_does_not_duplicate_existing_members(self):
        existing_name = NAMES[0]

        backup = self.create_backup({
            "members": [
                {
                    "name": existing_name,
                    "joined": "2026-09-01",
                    "left": None,
                },
            ],
            "expenses": [],
        })

        before = len(self.store.data["members"])

        merge(self.store, backup)

        self.assertEqual(
            len(self.store.data["members"]),
            before,
        )

    def test_merge_skips_deleted_expenses(self):
        backup = self.create_backup({
            "members": [],
            "expenses": [
                {
                    **self.valid_expense(),
                    "deleted": True,
                },
            ],
        })

        before = len(self.store.data["expenses"])

        added = merge(self.store, backup)

        self.assertEqual(added, 0)
        self.assertEqual(
            len(self.store.data["expenses"]),
            before,
        )

    def test_merge_assigns_new_expense_id(self):
        backup = self.create_backup({
            "members": [],
            "expenses": [
                self.valid_expense(eid=9999),
            ],
        })

        added = merge(self.store, backup)

        self.assertEqual(added, 1)

        expense = self.store.data["expenses"][-1]

        self.assertNotEqual(expense["id"], 9999)

    def test_merge_skips_invalid_expenses_and_reports_reason(self):
        backup = self.create_backup({
            "members": [],
            "expenses": [
                {
                    "id": 123,
                    "date": "잘못된 날짜",
                    "payer": NAMES[0],
                    "amount": 10000,
                    "members": [NAMES[0]],
                    "deleted": False,
                },
            ],
        })

        report = {}

        added = merge(self.store, backup, report=report)

        self.assertEqual(added, 0)
        self.assertEqual(len(report["skipped"]), 1)
        self.assertEqual(report["skipped"][0]["id"], 123)
        self.assertTrue(report["skipped"][0]["reason"])

    def test_merge_reports_duplicate_expenses(self):
        # 먼저 기존 지출을 정상적으로 생성한다.
        first_backup = self.create_backup({
            "members": [],
            "expenses": [
                self.valid_expense(eid=100),
            ],
        })

        first_added = merge(self.store, first_backup)
        self.assertEqual(first_added, 1)

        existing = self.store.data["expenses"][-1]

        # 동일 날짜·결제자·금액의 지출을 다시 병합한다.
        second_backup = self.create_backup({
            "members": [],
            "expenses": [
                {
                    **self.valid_expense(eid=456),
                    "date": existing["date"],
                    "payer": existing["payer"],
                    "amount": existing["amount"],
                    "members": existing["members"],
                },
            ],
        })

        report = {}

        merge(self.store, second_backup, report=report)

        self.assertEqual(len(report["duplicates"]), 1)
        self.assertEqual(report["duplicates"][0]["id"], 456)

    def test_merge_skips_member_with_invalid_dates(self):
        backup = self.create_backup({
            "members": [
                {"name": "가입일누락"},
                {"name": "날짜오류", "joined": "잘못된 날짜"},
                {"name": "탈퇴일오류", "joined": "2026-11-10", "left": "2026-11-01"},
            ],
            "expenses": [],
        })
        before = len(self.store.data["members"])
        report = {}

        merge(self.store, backup, report=report)

        self.assertEqual(len(self.store.data["members"]), before)
        self.assertEqual(len(report["skipped"]), 3)
        self.assertTrue(all(item["reason"] for item in report["skipped"]))

    def test_merge_reports_missing_expense_field(self):
        backup = self.create_backup({
            "members": [],
            "expenses": [{"id": 123, "payer": NAMES[0], "amount": 10000, "members": [NAMES[0]]}],
        })
        report = {}

        added = merge(self.store, backup, report=report)

        self.assertEqual(added, 0)
        self.assertEqual(report["skipped"][0]["reason"], "필수 항목이 없습니다: date")
