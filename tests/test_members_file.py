"""설정 파일 담당: 명부 파일 읽기(load_members_file) 테스트.

실행: python -m unittest discover -s tests -v
"""

import unittest

from helpers import StoreCase

from moim.features.expenses import load_members_file


class LoadMembersFile(StoreCase):
    def write(self, text):
        path = self.path("members.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def member(self, name):
        return self.store.member(name)

    def test_add_new_members(self):
        path = self.write("최하나,2026-10-01\n정두리,2026-10-05,2026-11-15\n")
        added, left, errors = load_members_file(self.store, path)
        self.assertEqual((added, left, errors), (["최하나", "정두리"], [], []))
        self.assertEqual(self.member("최하나")["left"], None)
        self.assertEqual(self.member("정두리")["left"], "2026-11-15")

    def test_skip_comments_and_blank_lines(self):
        path = self.write("# 명부\n\n최하나,2026-10-01\n   \n")
        added, left, errors = load_members_file(self.store, path)
        self.assertEqual((added, errors), (["최하나"], []))

    def test_existing_member_only_left_date(self):
        path = self.write("최하나,2026-10-01\n")
        load_members_file(self.store, path)
        path = self.write("최하나,2026-01-01,2026-11-20\n")
        added, left, errors = load_members_file(self.store, path)
        self.assertEqual((added, left, errors), ([], ["최하나"], []))
        self.assertEqual(self.member("최하나")["joined"], "2026-10-01")
        self.assertEqual(self.member("최하나")["left"], "2026-11-20")

    def test_existing_member_without_left_date_unchanged(self):
        path = self.write("최하나,2026-10-01\n")
        load_members_file(self.store, path)
        added, left, errors = load_members_file(self.store, path)
        self.assertEqual((added, left, errors), ([], [], []))

    def test_errors_report_line_numbers_and_continue(self):
        path = self.write("최하나,2026-10-01\n잘못된줄\n정두리,2026-13-01\n박세이,2026-10-10,2026-10-01\n한가온,2026-10-20\n")
        added, left, errors = load_members_file(self.store, path)
        self.assertEqual(added, ["최하나", "한가온"])
        self.assertEqual([no for no, _ in errors], [2, 3, 4])
        
    def add_expense(self, date, payer="김민수", members=("김민수", "이서연")):
        eid = self.store.new_id()
        self.store.data["expenses"].append(
            {"id": eid, "date": date, "payer": payer, "amount": 3000, "members": list(members),
             "category": None, "memo": "", "deleted": False})
        return eid

    def test_left_date_before_later_expense_is_error(self):
        eid = self.add_expense("2026-11-20")
        path = self.write("이서연,2026-09-01,2026-11-15\n")
        added, left, errors = load_members_file(self.store, path)
        self.assertEqual((added, left), ([], []))
        self.assertEqual([no for no, _ in errors], [1])
        self.assertIn(f"{eid}번", errors[0][1])
        self.assertIsNone(self.member("이서연")["left"])

    def test_left_date_on_last_expense_day_is_ok(self):
        self.add_expense("2026-11-20")
        path = self.write("이서연,2026-09-01,2026-11-20\n")
        added, left, errors = load_members_file(self.store, path)
        self.assertEqual((left, errors), (["이서연"], []))
        self.assertEqual(self.member("이서연")["left"], "2026-11-20")

    def test_deleted_expense_does_not_block_left_date(self):
        eid = self.add_expense("2026-11-20")
        self.store.get_expense(eid)["deleted"] = True
        path = self.write("이서연,2026-09-01,2026-11-15\n")
        added, left, errors = load_members_file(self.store, path)
        self.assertEqual((left, errors), (["이서연"], []))

    def test_payer_only_expense_also_blocks_left_date(self):
        self.add_expense("2026-11-20", payer="이서연", members=("김민수",))
        path = self.write("이서연,2026-09-01,2026-11-15\n")
        added, left, errors = load_members_file(self.store, path)
        self.assertEqual(left, [])
        self.assertEqual([no for no, _ in errors], [1])

    def test_blocked_line_skipped_and_other_lines_applied(self):
        self.add_expense("2026-11-20")
        path = self.write("이서연,2026-09-01,2026-11-15\n박지훈,2026-09-01,2026-11-15\n최하나,2026-10-01\n")
        added, left, errors = load_members_file(self.store, path)
        self.assertEqual((added, left), (["최하나"], ["박지훈"]))
        self.assertEqual([no for no, _ in errors], [1])
        self.assertIsNone(self.member("이서연")["left"])
        self.assertEqual(self.member("박지훈")["left"], "2026-11-15")
        
    def test_utf8_bom_file(self):
        path = self.path("bom.txt")
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("최하나,2026-10-01\n")
        added, left, errors = load_members_file(self.store, path)
        self.assertEqual(added, ["최하나"])


if __name__ == "__main__":
    unittest.main()
