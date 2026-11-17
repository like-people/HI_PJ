"""기능 5: 특정 날짜의 회원 목록과 명부 순서 검사."""
import datetime as dt
import unittest

from helpers import StoreCase, NAMES
from moim.common.queries import active_members


class ActiveMembersTests(StoreCase):
    def test_before_join(self):
        self.assertEqual(active_members(self.store, "2026-08-31"), [])

    def test_join_day(self):
        self.assertEqual(active_members(self.store, "2026-09-01"), NAMES)

    def test_leave_day(self):
        self.store.member(NAMES[0])["left"] = "2026-11-15"
        self.assertEqual(active_members(self.store, "2026-11-15"), NAMES)

    def test_after_leave(self):
        self.store.member(NAMES[0])["left"] = "2026-11-15"
        self.assertEqual(active_members(self.store, "2026-11-16"), NAMES[1:])

    def test_no_leave_date(self):
        self.assertEqual(active_members(self.store, "2027-01-01"), NAMES)

    def test_roster_order_with_inactive_member(self):
        roster = self.store.data["members"]
        self.store.data["members"] = [roster[2], roster[0], roster[1]]
        self.store.member(NAMES[0])["left"] = "2026-11-14"
        self.assertEqual(
            active_members(self.store, "2026-11-15"), [NAMES[2], NAMES[1]]
        )

    def test_all_members_left(self):
        for member in self.store.data["members"]:
            member["left"] = "2026-11-14"
        self.assertEqual(active_members(self.store, "2026-11-15"), [])

    def test_empty_roster(self):
        self.store.data["members"] = []
        self.assertEqual(active_members(self.store, "2026-11-15"), [])

    def test_date_object(self):
        self.assertEqual(active_members(self.store, dt.date(2026, 11, 15)), NAMES)


if __name__ == "__main__":
    unittest.main()
