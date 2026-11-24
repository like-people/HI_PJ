"""기능 1: 회원 추가(add_member)와 `member add` 명령 테스트."""

import datetime as dt
import unittest
from unittest.mock import patch

from helpers import NAMES, StoreCase
from moim.cli import main
from moim.common.store import Store
from moim.features import expenses


class AddMember(StoreCase):
    def test_adds_member_with_normalized_date(self):
        member = expenses.add_member(self.store, " 최하나 ", dt.date(2026, 11, 3))
        self.assertEqual(member, {"name": "최하나", "joined": "2026-11-03", "left": None})
        self.assertEqual(self.store.data["members"][-1], member)
        self.assertEqual([m["name"] for m in self.store.data["members"]], NAMES + ["최하나"])

    def test_new_member_can_join_expenses_from_join_day(self):
        expenses.add_member(self.store, "최하나", "2026-11-03")
        with self.assertRaisesRegex(ValueError, "참여자"):
            expenses.add_expense(self.store, "2026-11-02", NAMES[0], 1000, ["최하나"])
        expense, _ = expenses.add_expense(self.store, "2026-11-03", NAMES[0], 1000, ["최하나"])
        self.assertEqual(expense["members"], ["최하나"])

    def test_rejects_duplicate_name(self):
        with self.assertRaisesRegex(ValueError, "이미 명부"):
            expenses.add_member(self.store, NAMES[0], "2026-11-03")
        self.assertEqual(len(self.store.data["members"]), len(NAMES))

    def test_rejects_bad_name_or_date(self):
        for name in ("", "   ", None, "김;이", "김,이", "김=2"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                expenses.add_member(self.store, name, "2026-11-03")
        with self.assertRaisesRegex(ValueError, "날짜"):
            expenses.add_member(self.store, "최하나", "2026-02-30")
        self.assertEqual(len(self.store.data["members"]), len(NAMES))


class MemberAddCommand(StoreCase):
    def setUp(self):
        super().setUp()
        self.store.save()
        self.output = []

    def member(self, *args):
        self.output.clear()
        return main(["--config", self.path("config.json"), "member", *args], self.output.append)

    def test_add_is_saved(self):
        self.assertEqual(self.member("add", "최하나", "--joined", "2026-11-03"), 0)
        self.assertEqual(self.output, ["회원을 추가했습니다: 최하나 (가입일 2026-11-03)"])
        saved = Store(self.store.path).load().member("최하나")
        self.assertEqual(saved, {"name": "최하나", "joined": "2026-11-03", "left": None})

    def test_duplicate_is_error_without_saving(self):
        with patch.object(Store, "save", side_effect=AssertionError("오류 뒤 저장")):
            self.assertEqual(self.member("add", NAMES[0], "--joined", "2026-11-03"), 1)
        self.assertEqual(self.output, [f"오류: 이미 명부에 있는 이름입니다: {NAMES[0]}"])


if __name__ == "__main__":
    unittest.main()
