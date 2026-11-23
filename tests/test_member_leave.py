"""기능 1: 회원 탈퇴(leave_member)와 `member leave` 명령 테스트."""

import unittest
from unittest.mock import patch

from helpers import NAMES, StoreCase
from moim.cli import main
from moim.common.queries import is_member_active
from moim.common.store import Store
from moim.features import expenses

KIM, LEE, PARK = NAMES


class LeaveMember(StoreCase):
    def test_sets_left_and_leave_day_is_still_member(self):
        member = expenses.leave_member(self.store, LEE, "2026-11-15")
        self.assertEqual(member["left"], "2026-11-15")
        self.assertTrue(is_member_active(self.store, LEE, "2026-11-15"))
        self.assertFalse(is_member_active(self.store, LEE, "2026-11-16"))
        with self.assertRaisesRegex(ValueError, "참여자"):
            expenses.add_expense(self.store, "2026-11-16", KIM, 1000, [KIM, LEE])

    def test_leave_on_join_day_and_change_date(self):
        self.assertEqual(expenses.leave_member(self.store, LEE, "2026-09-01")["left"], "2026-09-01")
        self.assertEqual(expenses.leave_member(self.store, LEE, "2026-11-30")["left"], "2026-11-30")

    def test_rejects_unknown_member_and_left_before_join(self):
        with self.assertRaisesRegex(ValueError, "명부"):
            expenses.leave_member(self.store, "없는사람", "2026-11-15")
        with self.assertRaisesRegex(ValueError, "가입일"):
            expenses.leave_member(self.store, LEE, "2026-08-31")
        with self.assertRaisesRegex(ValueError, "날짜"):
            expenses.leave_member(self.store, LEE, "2026-13-01")
        self.assertIsNone(self.store.member(LEE)["left"])

    def test_rejects_when_later_expenses_include_member(self):
        expenses.add_expense(self.store, "2026-11-15", KIM, 3000, NAMES)
        later, _ = expenses.add_expense(self.store, "2026-11-16", KIM, 3000, [KIM, LEE])
        paid, _ = expenses.add_expense(self.store, "2026-11-20", LEE, 3000, [KIM])
        with self.assertRaisesRegex(ValueError, f"{later['id']}번, {paid['id']}번"):
            expenses.leave_member(self.store, LEE, "2026-11-15")
        self.assertIsNone(self.store.member(LEE)["left"])

    def test_deleted_later_expense_does_not_block(self):
        later, _ = expenses.add_expense(self.store, "2026-11-16", KIM, 3000, [KIM, LEE])
        expenses.delete_expense(self.store, later["id"])
        self.assertEqual(expenses.leave_member(self.store, LEE, "2026-11-15")["left"], "2026-11-15")


class MemberLeaveCommand(StoreCase):
    def setUp(self):
        super().setUp()
        self.store.save()
        self.output = []

    def member(self, *args):
        self.output.clear()
        return main(["--config", self.path("config.json"), "member", *args], self.output.append)

    def test_leave_is_saved(self):
        self.assertEqual(self.member("leave", LEE, "--date", "2026-11-15"), 0)
        self.assertEqual(self.output, [f"탈퇴를 기록했습니다: {LEE} (탈퇴일 2026-11-15)"])
        self.assertEqual(Store(self.store.path).load().member(LEE)["left"], "2026-11-15")

    def test_unknown_member_is_error_without_saving(self):
        with patch.object(Store, "save", side_effect=AssertionError("오류 뒤 저장")):
            self.assertEqual(self.member("leave", "없는사람", "--date", "2026-11-15"), 1)
        self.assertEqual(self.output, ["오류: 명부에 없는 회원입니다: 없는사람"])


if __name__ == "__main__":
    unittest.main()
