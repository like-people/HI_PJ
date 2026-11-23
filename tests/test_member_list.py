"""기능 1: 명부 목록(list_members)과 `member list` 명령 테스트."""

import unittest
from unittest.mock import patch

from helpers import NAMES, StoreCase
from moim.cli import main
from moim.common.store import Store
from moim.features import expenses

KIM, LEE, PARK = NAMES


class ListMembers(StoreCase):
    def test_roster_order_with_left_date(self):
        roster = self.store.data["members"]
        self.store.data["members"] = [roster[2], roster[0], roster[1]]
        self.store.member(LEE)["left"] = "2026-11-15"
        self.assertEqual(expenses.list_members(self.store), [
            {"name": PARK, "joined": "2026-09-01", "left": None},
            {"name": KIM, "joined": "2026-09-01", "left": None},
            {"name": LEE, "joined": "2026-09-01", "left": "2026-11-15"},
        ])

    def test_returns_copies(self):
        listed = expenses.list_members(self.store)
        listed[0]["left"] = "2026-11-15"
        listed.append({"name": "최하나", "joined": "2026-11-01", "left": None})
        self.assertIsNone(self.store.member(KIM)["left"])
        self.assertEqual(len(self.store.data["members"]), len(NAMES))

    def test_empty_roster(self):
        self.store.data["members"] = []
        self.assertEqual(expenses.list_members(self.store), [])


class MemberListCommand(StoreCase):
    def setUp(self):
        super().setUp()
        self.output = []

    def member(self, *args):
        self.store.save()
        self.output.clear()
        with patch.object(Store, "save", side_effect=AssertionError("조회 중 저장")):
            return main(["--config", self.path("config.json"), "member", *args], self.output.append)

    def test_table_in_roster_order(self):
        self.store.member(LEE)["left"] = "2026-11-15"
        self.assertEqual(self.member("list"), 0)
        lines = self.output[0].splitlines()
        self.assertEqual(lines[0].split(), ["이름", "가입일", "탈퇴일"])
        self.assertEqual([line.split() for line in lines[2:]], [
            [KIM, "2026-09-01", "-"],
            [LEE, "2026-09-01", "2026-11-15"],
            [PARK, "2026-09-01", "-"],
        ])

    def test_empty_roster(self):
        self.store.data["members"] = []
        self.assertEqual(self.member("list"), 0)
        self.assertEqual(self.output, ["명부에 회원이 없습니다."])


if __name__ == "__main__":
    unittest.main()
