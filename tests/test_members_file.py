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

    def test_utf8_bom_file(self):
        path = self.path("bom.txt")
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("최하나,2026-10-01\n")
        added, left, errors = load_members_file(self.store, path)
        self.assertEqual(added, ["최하나"])


if __name__ == "__main__":
    unittest.main()