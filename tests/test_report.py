"""기능 3 테스트: queries.expenses_in (보고서·정산 등이 쓰는 기간 조회).

실행: python -m unittest discover -s tests -v
"""

import datetime
import unittest

from helpers import NAMES, StoreCase

from moim.common import queries, textfmt
from moim.features import report

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


class BarChartTest(unittest.TestCase):
    def test_largest_fills_bar_width(self):
        got = textfmt.bar_chart({"식비": 30000, "교통": 15000}, bar_width=10)
        lines = got.splitlines()
        self.assertEqual(lines[0].count("#"), 10)
        self.assertEqual(lines[1].count("#"), 5)

    def test_value_with_commas_at_end(self):
        got = textfmt.bar_chart({"식비": 30000, "교통": 15000}, bar_width=10)
        self.assertEqual(got, "\n".join([
            "식비  ##########  30,000",
            "교통  #####       15,000",
        ]))

    def test_zero_has_no_bar_but_number(self):
        got = textfmt.bar_chart({"식비": 1000, "미분류": 0}, bar_width=5)
        zero_line = got.splitlines()[1]
        self.assertNotIn("#", zero_line)
        self.assertTrue(zero_line.endswith("0"))

    def test_negative_has_no_bar_but_number(self):
        got = textfmt.bar_chart({"식비": 1000, "환불": -500}, bar_width=5)
        negative_line = got.splitlines()[1]
        self.assertNotIn("#", negative_line)
        self.assertTrue(negative_line.endswith("-500"))

    def test_small_positive_gets_one_char(self):
        got = textfmt.bar_chart({"식비": 30000, "기타": 1}, bar_width=10)
        self.assertEqual(got.splitlines()[1].count("#"), 1)

    def test_all_zero_has_no_bars(self):
        got = textfmt.bar_chart({"a": 0, "b": 0}, bar_width=5)
        self.assertNotIn("#", got)

    def test_custom_char(self):
        got = textfmt.bar_chart({"a": 3, "b": 1}, bar_width=4, char="*")
        self.assertEqual(got.splitlines()[0].count("*"), 4)
        self.assertNotIn("#", got)

    def test_korean_names_align(self):
        got = textfmt.bar_chart({"김": 1000, "김민수": 500}, bar_width=5)
        starts = {textfmt.width(line.split("#")[0]) for line in got.splitlines()}
        self.assertEqual(len(starts), 1)

    def test_empty(self):
        self.assertEqual(textfmt.bar_chart({}), "")


class ReportTotals(StoreCase):
    def put(self, eid, date, payer, amount, category=None, deleted=None):
        e = {"id": eid, "date": date, "payer": payer, "amount": amount,
             "members": list(NAMES), "category": category, "memo": ""}
        if deleted is not None:
            e["deleted"] = deleted
        self.store.data["expenses"].append(e)

    def fill(self):
        kim, lee, park = NAMES
        self.put(1, "2026-10-15", kim, 3000, "식비")
        self.put(2, "2026-11-12", lee, 6000, "식비")
        self.put(3, "2026-11-13", kim, 9000, "교통")
        self.put(4, "2026-11-14", park, 500, "식비", deleted=True)

    def test_monthly_one_month(self):
        self.fill()
        self.assertEqual(report.monthly_totals(self.store, "2026-11", "2026-11"), {"2026-11": 15000})

    def test_monthly_range_includes_empty_month(self):
        self.fill()
             self.assertEqual(report.monthly_totals(self.store, "2026-10", "2026-12"),
                         {"2026-10": 3000, "2026-11": 15000, "2026-12": 0})

    def test_monthly_over_year_end(self):
        self.put(1, "2026-12-31", NAMES[0], 100)
        self.put(2, "2027-01-01", NAMES[0], 200)
        self.assertEqual(report.monthly_totals(self.store, "2026-12", "2027-01"),
                         {"2026-12": 100, "2027-01": 200})

    def test_monthly_leap_february_end(self):
        self.put(1, "2028-02-29", NAMES[0], 700)
        self.assertEqual(report.monthly_totals(self.store, "2028-02", "2028-02"), {"2028-02": 700})

    def test_monthly_skips_deleted(self):
        self.fill()
        self.assertEqual(report.monthly_totals(self.store, "2026-11", "2026-11")["2026-11"], 15000)

    def test_monthly_reversed_is_empty(self):
        self.fill()
        self.assertEqual(report.monthly_totals(self.store, "2026-12", "2026-10"), {})

    def test_monthly_bad_month_text(self):
        with self.assertRaises(ValueError):
            report.monthly_totals(self.store, "2026-13", "2026-12")

    def test_summary_total_matches_expenses(self):
        self.fill()
        got = report.period_summary(self.store, "2026-11-10", "2026-11-20")
        self.assertEqual(got["total"], 15000)

    def test_summary_by_category_big_first(self):
        self.fill()
        got = report.period_summary(self.store, "2026-11-10", "2026-11-20")
        self.assertEqual(list(got["by_category"].items()), [("교통", 9000), ("식비", 6000)])

    def test_summary_by_person(self):
        self.fill()
        kim, lee, park = NAMES
        got = report.period_summary(self.store, "2026-11-10", "2026-11-20")
        self.assertEqual(got["by_person"], {kim: 9000, lee: 6000})

    def test_summary_keys(self):
        got = report.period_summary(self.store, "2026-11-10", "2026-11-20")
        self.assertEqual(set(got), {"total", "by_category", "by_person"})

    def test_summary_empty_period(self):
        got = report.period_summary(self.store, "2026-11-10", "2026-11-20")
        self.assertEqual(got, {"total": 0, "by_category": {}, "by_person": {}})


if __name__ == "__main__":
    unittest.main()
