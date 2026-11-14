"""기능 5: 회원 기간 확인 테스트."""
import unittest

from helpers import StoreCase, NAMES
from moim.common.queries import is_member_active


class MemberActiveTests(StoreCase):
    def test_join_day(self):
        self.assertTrue(
            is_member_active(self.store, NAMES[0], "2026-09-01")
        )

    def test_before_join(self):
        self.assertFalse(
            is_member_active(self.store, NAMES[0], "2026-08-31")
        )

    def test_leave_day(self):
        self.store.member(NAMES[0])["left"] = "2026-11-15"
        self.assertTrue(
            is_member_active(self.store, NAMES[0], "2026-11-15")
        )

    def test_after_leave(self):
        self.store.member(NAMES[0])["left"] = "2026-11-15"
        self.assertFalse(
            is_member_active(self.store, NAMES[0], "2026-11-16")
        )

    def test_no_leave_date(self):
        self.assertTrue(
            is_member_active(self.store, NAMES[0], "2027-01-01")
        )

    def test_unknown_member(self):
        self.assertFalse(
            is_member_active(self.store, "없는사람", "2026-11-15")
        )


if __name__ == "__main__":
    unittest.main()
