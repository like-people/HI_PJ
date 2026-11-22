"""명령 묶음 report(commands/report.py) 테스트.

moim.cli.main 으로 명령을 직접 실행해 화면 출력, 종료 코드, 저장한 파일을 확인한다.
실행: python -m unittest discover -s tests -v
"""

import json
import unittest

from helpers import NAMES, StoreCase

from moim.cli import main


class ReportCommandCase(StoreCase):
    def setUp(self):
        super().setUp()
        self.config = self.path("config.json")
        with open(self.config, "w", encoding="utf-8") as f:
            json.dump({"data": self.path("data.json")}, f)
        kim, lee, park = NAMES
        self.put(1, "2026-10-05", kim, 3000, "식비", "10월 점심")
        self.put(2, "2026-11-12", lee, 6000, "식비", "점심 식대")
        self.put(3, "2026-11-13", kim, 9000, "교통", "택시")
        self.put(4, "2026-11-20", park, 2400, None, "")
        self.store.save()

    def put(self, eid, date, payer, amount, category, memo):
        self.store.data["expenses"].append(
            {"id": eid, "date": date, "payer": payer, "amount": amount,
             "members": list(NAMES), "category": category, "memo": memo})

    def report(self, *args):
        output = []
        code = main(["--config", self.config, "report", *args], output.append)
        return code, "\n".join(output)

    def data_text(self):
        with open(self.path("data.json"), encoding="utf-8") as f:
            return f.read()


class PeriodAndMonthly(ReportCommandCase):
    def test_period_by_start_and_end(self):
        code, text = self.report("period", "--start", "2026-11-10", "--end", "2026-11-20")
        self.assertEqual(code, 0)
        self.assertIn("기간 보고서 (2026-11-10 ~ 2026-11-20)", text)
        self.assertIn("합계: 17,400원 (3건)", text)
        for part in ["[분류별]", "[사람별 낸 돈]", "[요일별]", "미분류"]:
            self.assertIn(part, text)

    def test_period_by_month_matches_month_total(self):
        code, text = self.report("period", "--month", "2026-11")
        self.assertIn("합계: 17,400원", text)

    def test_period_without_range_is_error(self):
        code, text = self.report("period")
        self.assertEqual(code, 1)
        self.assertIn("기간을 지정", text)

    def test_period_reversed_is_error(self):
        code, text = self.report("period", "--start", "2026-11-20", "--end", "2026-11-10")
        self.assertEqual((code, text), (1, "오류: 시작일이 끝일보다 늦습니다"))

    def test_period_empty(self):
        code, text = self.report("period", "--start", "2026-12-01", "--end", "2026-12-31")
        self.assertEqual(code, 0)
        self.assertIn("이 기간에는 지출이 없습니다.", text)

    def test_monthly_table_with_total(self):
        code, text = self.report("monthly", "2026-10", "2026-11")
        self.assertEqual(code, 0)
        self.assertIn("2026-10", text)
        self.assertIn("17,400", text)
        self.assertIn("20,400", text)

    def test_monthly_reversed_is_error(self):
        self.assertEqual(self.report("monthly", "2026-12", "2026-10"),
                         (1, "오류: 시작 달이 끝 달보다 늦습니다"))

    def test_report_does_not_change_data_file(self):
        before = self.data_text()
        self.report("period", "--month", "2026-11")
        self.report("monthly", "2026-10", "2026-11")
        self.report("month", "2026-11")
        self.report("search", "--word", "점심")
        self.report("weekday", "--month", "2026-11")
        self.report("week", "--month", "2026-11")
        self.report("top", "--month", "2026-11")
        self.assertEqual(self.data_text(), before)

    def test_no_subcommand_shows_usage(self):
        code, text = self.report()
        self.assertEqual(code, 0)
        self.assertIn("사용법: report", text)


class MonthCommand(ReportCommandCase):
    def test_month_prints_report(self):
        code, text = self.report("month", "2026-11")
        self.assertEqual(code, 0)
        self.assertIn("2026-11 월별 보고서 (2026-11-01 ~ 2026-11-30)", text)
        self.assertIn("합계: 17,400원 (3건)", text)

    def test_month_bad_month_is_error(self):
        code, text = self.report("month", "2026-13")
        self.assertEqual(code, 1)
        self.assertTrue(text.startswith("오류: "))

    def test_month_empty(self):
        code, text = self.report("month", "2026-12")
        self.assertEqual(code, 0)
        self.assertIn("이 달에는 지출이 없습니다.", text)


class SearchCommand(ReportCommandCase):
    def test_search_word_and_total_row(self):
        code, text = self.report("search", "--word", "점심")
        self.assertEqual(code, 0)
        self.assertIn("10월 점심", text)
        self.assertIn("점심 식대", text)
        self.assertNotIn("택시", text)
        self.assertIn("9,000", text)

    def test_search_amount_range_and_month(self):
        code, text = self.report("search", "--month", "2026-11", "--min-amount", "6,000", "--max-amount", "6000")
        self.assertIn("점심 식대", text)
        self.assertNotIn("택시", text)

    def test_search_person(self):
        code, text = self.report("search", "--person", NAMES[2], "--word", "택시")
        self.assertIn("택시", text)

    def test_search_nothing_found(self):
        self.assertEqual(self.report("search", "--word", "없는낱말"), (0, "찾은 지출이 없습니다."))


class SaveOption(ReportCommandCase):
    def test_month_save_writes_txt_and_does_not_print_report(self):
        path = self.path("r.txt")
        code, text = self.report("month", "2026-11", "--save", path)
        self.assertEqual((code, text), (0, f"저장했습니다: {path}"))
        with open(path, encoding="utf-8") as f:
            self.assertIn("합계: 17,400원 (3건)", f.read())

    def test_month_save_rejects_non_txt(self):
        code, text = self.report("month", "2026-11", "--save", self.path("r.csv"))
        self.assertEqual(code, 1)
        self.assertIn(".txt", text)

    def test_period_save_writes_txt(self):
        path = self.path("p.txt")
        code, text = self.report("period", "--month", "2026-11", "--save", path)
        self.assertEqual((code, text), (0, f"저장했습니다: {path}"))
        with open(path, encoding="utf-8") as f:
            self.assertIn("기간 보고서", f.read())


class WeekdayWeekTop(ReportCommandCase):
    def test_weekday_shows_all_seven_days(self):
        code, text = self.report("weekday", "--month", "2026-11")
        self.assertEqual(code, 0)
        self.assertEqual([line[0] for line in text.splitlines()], list("월화수목금토일"))

    def test_weekday_reversed_is_error(self):
        code, text = self.report("weekday", "--start", "2026-11-20", "--end", "2026-11-10")
        self.assertEqual((code, text), (1, "오류: 시작일이 끝일보다 늦습니다"))

    def test_week_lists_monday_keys(self):
        code, text = self.report("week", "--month", "2026-11")
        self.assertEqual(code, 0)
        self.assertIn("2026-11-09", text)
        self.assertIn("15,000", text)

    def test_week_reversed_is_error(self):
        code, text = self.report("week", "--start", "2026-11-30", "--end", "2026-11-01")
        self.assertEqual((code, text), (1, "오류: 시작일이 끝일보다 늦습니다"))

    def test_top_default_big_first(self):
        code, text = self.report("top", "--month", "2026-11")
        self.assertEqual(code, 0)
        self.assertLess(text.index("택시"), text.index("점심 식대"))

    def test_top_count(self):
        code, text = self.report("top", "--month", "2026-11", "-n", "1")
        self.assertIn("택시", text)
        self.assertNotIn("점심 식대", text)

    def test_top_zero_count_is_error(self):
        self.assertEqual(self.report("top", "--month", "2026-11", "-n", "0"),
                         (1, "오류: 건수는 1 이상이어야 합니다"))

    def test_top_empty(self):
        self.assertEqual(self.report("top", "--month", "2026-12"), (0, "지출이 없습니다."))


if __name__ == "__main__":
    unittest.main()
