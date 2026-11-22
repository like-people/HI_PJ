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


class ReportCompare(StoreCase):
    def put(self, eid, date, amount, deleted=None):
        e = {"id": eid, "date": date, "payer": NAMES[0], "amount": amount,
             "members": list(NAMES), "category": None, "memo": ""}
        if deleted is not None:
            e["deleted"] = deleted
        self.store.data["expenses"].append(e)

    def test_month_over_month_increase(self):
        self.put(1, "2026-10-05", 3000)
        self.put(2, "2026-11-12", 15000)
        self.assertEqual(report.month_over_month(self.store, "2026-11"), (15000, 3000, 12000, 400))

    def test_month_over_month_decrease(self):
        self.put(1, "2026-10-05", 15000)
        self.put(2, "2026-11-12", 3000)
        self.assertEqual(report.month_over_month(self.store, "2026-11"), (3000, 15000, -12000, -80))

    def test_month_over_month_last_month_zero_has_no_percent(self):
        self.put(1, "2026-11-12", 3000)
        self.assertEqual(report.month_over_month(self.store, "2026-11"), (3000, 0, 3000, None))

    def test_month_over_month_both_zero(self):
        self.assertEqual(report.month_over_month(self.store, "2026-11"), (0, 0, 0, None))

    def test_month_over_month_rounds_half_away_from_zero(self):
        self.put(1, "2026-10-05", 8)
        self.put(2, "2026-11-05", 9)    # +12.5% -> 13
        self.put(3, "2026-08-05", 8)
        self.put(4, "2026-09-05", 7)    # -12.5% -> -13
        self.assertEqual(report.month_over_month(self.store, "2026-11")[3], 13)
        self.assertEqual(report.month_over_month(self.store, "2026-09")[3], -13)

    def test_month_over_month_across_year(self):
        self.put(1, "2026-12-10", 1000)
        self.put(2, "2027-01-10", 1500)
        self.assertEqual(report.month_over_month(self.store, "2027-01"), (1500, 1000, 500, 50))

    def test_month_over_month_skips_deleted(self):
        self.put(1, "2026-10-05", 1000)
        self.put(2, "2026-10-06", 9000, deleted=True)
        self.put(3, "2026-11-05", 1000)
        self.assertEqual(report.month_over_month(self.store, "2026-11"), (1000, 1000, 0, 0))

    def test_weekday_totals_has_all_seven_days(self):
        got = report.weekday_totals(self.store, "2026-11-01", "2026-11-30")
        self.assertEqual(list(got), ["월", "화", "수", "목", "금", "토", "일"])
        self.assertEqual(sum(got.values()), 0)

    def test_weekday_totals_sums_by_weekday(self):
        self.put(1, "2026-11-12", 6000)   # 목요일
        self.put(2, "2026-11-19", 1000)   # 목요일
        self.put(3, "2026-11-13", 9000)   # 금요일
        self.put(4, "2026-11-14", 500, deleted=True)
        got = report.weekday_totals(self.store, "2026-11-01", "2026-11-30")
        self.assertEqual(got["목"], 7000)
        self.assertEqual(got["금"], 9000)
        self.assertEqual(got["토"], 0)

    def test_week_totals_monday_keys(self):
        self.put(1, "2026-11-15", 100)    # 일요일: 11/09 주
        self.put(2, "2026-11-16", 200)    # 월요일: 11/16 주
        got = report.week_totals(self.store, "2026-11-09", "2026-11-22")
        self.assertEqual(got, {"2026-11-09": 100, "2026-11-16": 200})

    def test_week_totals_includes_empty_weeks_and_partial_first_week(self):
        self.put(1, "2026-11-12", 500)
        got = report.week_totals(self.store, "2026-11-12", "2026-11-30")
        self.assertEqual(list(got), ["2026-11-09", "2026-11-16", "2026-11-23", "2026-11-30"])
        self.assertEqual(got["2026-11-09"], 500)

    def test_week_totals_reversed_is_empty(self):
        self.assertEqual(report.week_totals(self.store, "2026-11-30", "2026-11-01"), {})


class ReportQuery(StoreCase):
    S, E = "2026-11-01", "2026-11-30"

    def put(self, eid, date, payer, amount, members=None, memo="", deleted=None):
        e = {"id": eid, "date": date, "payer": payer, "amount": amount,
             "members": list(members or NAMES), "category": None, "memo": memo}
        if deleted is not None:
            e["deleted"] = deleted
        self.store.data["expenses"].append(e)

    def fill(self):
        kim, lee, park = NAMES
        self.put(1, "2026-11-10", kim, 5000, memo="점심 식대")
        self.put(2, "2026-11-10", lee, 7000, members=[lee, park], memo="커피")
        self.put(3, "2026-11-12", park, 7000, members=[park], memo="점심")
        self.put(4, "2026-11-13", kim, 99999, deleted=True)
        self.put(5, "2026-12-01", kim, 100)

    def ids(self, **kw):
        return [e["id"] for e in report.search(self.store, **kw)]

    def test_top_expenses_big_first_then_date_then_id(self):
        self.fill()
        got = report.top_expenses(self.store, self.S, self.E)
        self.assertEqual([e["id"] for e in got], [2, 3, 1])

    def test_top_expenses_limit_n(self):
        self.fill()
        self.assertEqual([e["id"] for e in report.top_expenses(self.store, self.S, self.E, 2)], [2, 3])

    def test_top_expenses_zero_n_is_empty(self):
        self.fill()
        self.assertEqual(report.top_expenses(self.store, self.S, self.E, 0), [])

    def test_top_expenses_skips_deleted(self):
        self.fill()
        got = report.top_expenses(self.store, self.S, self.E)
        self.assertNotIn(4, [e["id"] for e in got])

    def test_biggest_day(self):
        self.fill()
        self.assertEqual(report.biggest_day(self.store, self.S, self.E), ("2026-11-10", 12000))

    def test_biggest_day_tie_picks_earlier_date(self):
        self.put(1, "2026-11-12", NAMES[0], 500)
        self.put(2, "2026-11-05", NAMES[0], 500)
        self.assertEqual(report.biggest_day(self.store, self.S, self.E), ("2026-11-05", 500))

    def test_biggest_day_none_when_no_expense(self):
        self.assertIsNone(report.biggest_day(self.store, self.S, self.E))

    def test_search_all_without_conditions(self):
        self.fill()
        self.assertEqual(self.ids(), [1, 2, 3, 5])

    def test_search_period_start_and_end_only(self):
        self.fill()
        self.assertEqual(self.ids(start="2026-11-11"), [3, 5])
        self.assertEqual(self.ids(end="2026-11-10"), [1, 2])

    def test_search_person_payer_or_member(self):
        self.fill()
        kim, lee, park = NAMES
        self.assertEqual(self.ids(person=kim), [1, 5])
        self.assertEqual(self.ids(person=lee), [1, 2, 5])
        self.assertEqual(self.ids(person=park), [1, 2, 3, 5])

    def test_search_amount_range_includes_edges(self):
        self.fill()
        self.assertEqual(self.ids(min_amount=7000), [2, 3])
        self.assertEqual(self.ids(max_amount="5,000"), [1, 5])
        self.assertEqual(self.ids(min_amount=5000, max_amount=7000), [1, 2, 3])

    def test_search_word_in_memo(self):
        self.fill()
        self.assertEqual(self.ids(word="점심"), [1, 3])
        self.assertEqual(self.ids(word="없는낱말"), [])

    def test_search_combines_conditions(self):
        self.fill()
        self.assertEqual(self.ids(person=NAMES[1], word="커피"), [2])

    def test_search_skips_deleted(self):
        self.fill()
        self.assertNotIn(4, self.ids())

    def test_search_sorted_by_date_then_id(self):
        self.put(3, "2026-11-10", NAMES[0], 1)
        self.put(1, "2026-11-12", NAMES[0], 1)
        self.put(2, "2026-11-10", NAMES[0], 1)
        self.assertEqual(self.ids(), [2, 3, 1])

    def test_search_impossible_range_is_empty(self):
        self.fill()
        self.assertEqual(self.ids(min_amount=8000, max_amount=1000), [])


class ReportText(StoreCase):
    def put(self, eid, date, payer, amount, category=None, memo="", deleted=None):
        e = {"id": eid, "date": date, "payer": payer, "amount": amount,
             "members": list(NAMES), "category": category, "memo": memo}
        if deleted is not None:
            e["deleted"] = deleted
        self.store.data["expenses"].append(e)

    def fill(self):
        kim, lee, park = NAMES
        self.put(1, "2026-10-05", kim, 3000, "식비", "10월 점심")
        self.put(2, "2026-11-12", lee, 6000, "식비", "점심 식대")
        self.put(3, "2026-11-13", kim, 9000, "교통", "택시")
        self.put(4, "2026-11-14", park, 500, "식비", "삭제됨", deleted=True)
        self.put(5, "2026-11-20", park, 2400)

    def test_title_and_total(self):
        self.fill()
        text = report.month_report(self.store, "2026-11")
        self.assertIn("2026-11 월별 보고서 (2026-11-01 ~ 2026-11-30)", text)
        self.assertIn("합계: 17,400원 (3건)", text)

    def test_total_matches_period_total(self):
        self.fill()
        text = report.month_report(self.store, "2026-11")
        total = queries.period_total(self.store, "2026-11-01", "2026-11-30")
        self.assertIn(f"합계: {total:,}원", text)

    def test_has_all_sections(self):
        self.fill()
        text = report.month_report(self.store, "2026-11")
        for part in ["[분류별]", "[사람별 낸 돈]", "[요일별]", "[큰 지출 5건]",
                     "가장 많이 쓴 날: 2026-11-13 (9,000원)"]:
            self.assertIn(part, text)

    def test_month_over_month_line(self):
        self.fill()
        text = report.month_report(self.store, "2026-11")
        self.assertIn("전월 대비: 지난달 3,000원, +14,400원 (+480%)", text)

    def test_no_last_month_message(self):
        self.fill()
        text = report.month_report(self.store, "2026-10")
        self.assertIn("지난달 지출이 없어 비교하지 않습니다", text)

    def test_deleted_expense_skipped(self):
        self.fill()
        text = report.month_report(self.store, "2026-11")
        self.assertNotIn("삭제됨", text)

    def test_uncategorized_label(self):
        self.fill()
        text = report.month_report(self.store, "2026-11")
        self.assertIn("미분류", text)

    def test_empty_month(self):
        self.fill()
        text = report.month_report(self.store, "2026-12")
        self.assertIn("이 달에는 지출이 없습니다.", text)
        self.assertNotIn("[분류별]", text)

    def test_bad_month_raises(self):
        with self.assertRaises(ValueError):
            report.month_report(self.store, "2026-13")

    def test_save_report_writes_file(self):
        path = self.path("r.txt")
        got = report.save_report("안녕\n둘째 줄", path)
        self.assertEqual(got, path)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "안녕\n둘째 줄\n")

    def test_save_report_single_trailing_newline(self):
        path = self.path("r.txt")
        report.save_report("끝\n", path)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "끝\n")

    def test_save_report_rejects_non_txt(self):
        with self.assertRaises(ValueError):
            report.save_report("x", self.path("r.csv"))

    def test_save_report_missing_folder(self):
        with self.assertRaises(FileNotFoundError):
            report.save_report("x", self.path("없는폴더/r.txt"))
            
            
if __name__ == "__main__":
    unittest.main()
