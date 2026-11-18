"""기능 3 테스트: queries.expenses_in (보고서·정산 등이 쓰는 기간 조회).

실행: python -m unittest discover -s tests -v
"""

import datetime
import unittest

from helpers import NAMES, StoreCase

from moim.common import queries, textfmt

KIM = NAMES[0]


class ExpensesIn(StoreCase):
    def put(self, eid, date, deleted=None):
        """기능 1(add_expense) 없이도 돌도록 지출 dict 를 자료에 직접 넣는다."""
        e = {"id": eid, "date": date, "payer": KIM, "amount": 1000,
             "members": list(NAMES), "category": None, "memo": ""}
        if deleted is not None:
            e["deleted"] = deleted
        self.store.data["expenses"].append(e)
        return e

    def ids(self, start, end, **kw):
        return [e["id"] for e in queries.expenses_in(self.store, start, end, **kw)]

    def test_includes_start_and_end(self):
        self.put(1, "2026-10-31")
        self.put(2, "2026-11-01")
        self.put(3, "2026-11-30")
        self.put(4, "2026-12-01")
        self.assertEqual(self.ids("2026-11-01", "2026-11-30"), [2, 3])

    def test_skips_deleted_by_default(self):
        self.put(1, "2026-11-05", deleted=True)
        self.put(2, "2026-11-06", deleted=False)
        self.assertEqual(self.ids("2026-11-01", "2026-11-30"), [2])

    def test_include_deleted(self):
        self.put(1, "2026-11-05", deleted=True)
        self.put(2, "2026-11-06")
        self.assertEqual(self.ids("2026-11-01", "2026-11-30", include_deleted=True), [1, 2])

    def test_old_data_without_deleted_key(self):
        self.put(1, "2026-11-05")  # deleted 키가 없는 옛 자료
        self.assertEqual(self.ids("2026-11-01", "2026-11-30"), [1])

    def test_sorted_by_date_then_id(self):
        self.put(3, "2026-11-10")
        self.put(1, "2026-11-12")
        self.put(2, "2026-11-10")
        self.assertEqual(self.ids("2026-11-01", "2026-11-30"), [2, 3, 1])

    def test_accepts_date_objects(self):
        self.put(1, "2026-11-15")
        got = queries.expenses_in(self.store, datetime.date(2026, 11, 1), datetime.date(2026, 11, 30))
        self.assertEqual([e["id"] for e in got], [1])

    def test_returns_original_dicts(self):
        e = self.put(1, "2026-11-15")
        self.assertIs(queries.expenses_in(self.store, "2026-11-01", "2026-11-30")[0], e)

    def test_empty(self):
        self.assertEqual(queries.expenses_in(self.store, "2026-11-01", "2026-11-30"), [])


class PersonPaid(StoreCase):
    def put(self, eid, date, payer, amount, deleted=None):
        e = {"id": eid, "date": date, "payer": payer, "amount": amount,
             "members": list(NAMES), "category": None, "memo": ""}
        if deleted is not None:
            e["deleted"] = deleted
        self.store.data["expenses"].append(e)

    def paid(self, start="2026-11-10", end="2026-11-20"):
        return queries.person_paid(self.store, start, end)

    def test_sums_by_payer(self):
        kim, lee, park = NAMES
        self.put(1, "2026-11-12", lee, 6000)
        self.put(2, "2026-11-13", kim, 9000)
        self.put(3, "2026-11-14", kim, 1000)
        self.assertEqual(self.paid(), {kim: 10000, lee: 6000})

    def test_member_order_and_only_payers(self):
        kim, lee, park = NAMES
        self.put(1, "2026-11-12", park, 3000)
        self.put(2, "2026-11-13", kim, 2000)
        self.assertEqual(list(self.paid()), [kim, park])

    def test_skips_deleted(self):
        kim = NAMES[0]
        self.put(1, "2026-11-12", kim, 5000, deleted=True)
        self.put(2, "2026-11-13", kim, 1000)
        self.assertEqual(self.paid(), {kim: 1000})

    def test_period_includes_start_and_end(self):
        kim = NAMES[0]
        self.put(1, "2026-10-31", kim, 1)
        self.put(2, "2026-11-01", kim, 10)
        self.put(3, "2026-11-30", kim, 100)
        self.put(4, "2026-12-01", kim, 1000)
        self.assertEqual(self.paid("2026-11-01", "2026-11-30"), {kim: 110})

    def test_empty(self):
        self.assertEqual(self.paid(), {})


class TableTest(unittest.TestCase):
    HEAD = ["번호", "이름", "금액"]

    def test_commas_and_right_align(self):
        got = textfmt.table(self.HEAD, [[1, "김민수", 1500], [2, "이서연", 12000]], numeric={2})
        want = "\n".join([
            "번호  이름      금액",
            "--------------------",
            "1     김민수   1,500",
            "2     이서연  12,000",
        ])
        self.assertEqual(got, want)

    def test_total_row_is_whole_line(self):
        got = textfmt.table(self.HEAD, [[1, "김민수", 1500], [2, "이서연", 12000]],
                            total=["합계", "", 13500], numeric={2})
        self.assertEqual(got.splitlines()[-2], "-" * 20)
        self.assertEqual(got.splitlines()[-1], "합계          13,500")

    def test_no_total_line_when_none(self):
        got = textfmt.table(self.HEAD, [[1, "김민수", 1500]], numeric={2})
        self.assertEqual(len(got.splitlines()), 3)

    def test_non_numeric_column_keeps_digits(self):
        got = textfmt.table(["번호", "금액"], [[1234, 5000]], numeric={1})
        self.assertIn("1234", got)
        self.assertIn("5,000", got)
        self.assertNotIn("1,234", got)

    def test_negative_number(self):
        got = textfmt.table(["번호", "금액"], [[1, -5000]], numeric={1})
        self.assertIn("-5,000", got)

    def test_korean_width_aligns(self):
        got = textfmt.table(["이름", "금액"], [["김", 1], ["김민수", 22]], numeric={1})
        widths = {textfmt.width(line) for line in got.splitlines() if not line.startswith("-")}
        self.assertEqual(len(widths), 1)

    def test_empty_rows(self):
        self.assertEqual(textfmt.table(["이름"], []), "이름\n----")


if __name__ == "__main__":
    unittest.main()
