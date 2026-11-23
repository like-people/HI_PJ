"""통합 시나리오 테스트. 담당: 김영광.

한 달(2026-11)치 자료로 입력 → 분류 → 보고서 → 정산 → 내보내기를 이어서 실행하고,
같은 기간에서 다섯 합계가 모두 같은지 확인한다(규격 6-2 4번).
  보고서 합계(period_summary 의 total) = period_total = balances 의 paid 합
  = member_shares 합 = 내보낸 CSV 의 amount 합
"""

import unittest

from helpers import NAMES, StoreCase

from moim.common import queries
from moim.features import budget, categorize, expenses, report, settle, transfer_io

KIM, LEE, PARK = NAMES
START, END = "2026-11-01", "2026-11-30"

# 11월 지출 합계: 30,000 + 12,000(10,000 에서 수정) + 25,000 + 10,001 + 6,000(반복) = 83,001
# 10월 50,000 은 기간 밖, 11/20 9,000 은 삭제라 빠진다.
NOV_TOTAL = 83001
NOV_COUNT = 5
FOOD = 30000 + 25000  # 규칙으로 "식비"가 되는 지출


class Scenario(StoreCase):
    def setUp(self):
        super().setUp()
        # 1. 입력(기능 1 + 반복 지출)
        add = expenses.add_expense
        add(self.store, "2026-10-30", KIM, 50000, NAMES, memo="대관료")  # 기간 밖
        self.lunch, _ = add(self.store, "2026-11-02", KIM, "30,000", NAMES, memo="점심 식당")
        self.taxi, _ = add(self.store, "2026-11-05", LEE, 10000, NAMES, memo="택시")
        self.dinner, _ = add(self.store, "2026-11-10", PARK, 25000, NAMES, memo="회식 식당",
                             weights={KIM: 2, LEE: 2, PARK: 1})
        self.cafe, _ = add(self.store, "2026-11-15", KIM, 10001, [KIM, LEE], memo="카페")
        self.dropped, _ = add(self.store, "2026-11-20", LEE, 9000, [LEE, PARK], memo="택시")
        expenses.edit_expense(self.store, self.taxi["id"], amount=12000)
        expenses.delete_expense(self.store, self.dropped["id"])
        settle.add_recurring(self.store, 25, KIM, 6000, NAMES, "정기 대관료", "2026-11")
        settle.run_recurring(self.store, END)

        # 2. 분류(기능 2)
        self.rules = []
        categorize.add_rule(self.rules, "식비", keywords=["식당"])
        categorize.add_rule(self.rules, "교통", keywords=["택시"])
        categorize.apply_rules(self.store, self.rules)
        categorize.set_category(self.store, self.cafe["id"], "간식")

    def export_total(self, name, category=None):
        path = self.path(name)
        transfer_io.export_csv(self.store, path, START, END, category)
        return transfer_io.file_total(path)

    def five_totals(self):
        """규격 6-2 4번의 다섯 합계. 어느 값이 어긋났는지 보이도록 이름을 붙인다."""
        return {
            "보고서 total": report.period_summary(self.store, START, END)["total"],
            "period_total": queries.period_total(self.store, START, END),
            "balances paid 합": sum(r["paid"] for r in settle.balances(self.store, START, END).values()),
            "member_shares 합": sum(queries.member_shares(self.store, START, END).values()),
            "내보낸 CSV amount 합": self.export_total("all.csv")[1],
        }

    def assert_all_equal(self, expected):
        totals = self.five_totals()
        wrong = {name: value for name, value in totals.items() if value != expected}
        self.assertEqual(wrong, {}, f"합계 {expected:,} 와 다른 값: {wrong}")

    # 3~5. 보고서 · 정산 · 내보내기 합계 비교
    def test_five_totals_are_equal(self):
        self.assert_all_equal(NOV_TOTAL)

    def test_export_count_matches_period(self):
        self.assertEqual(self.export_total("all.csv"), (NOV_COUNT, NOV_TOTAL))
        self.assertEqual(len(queries.expenses_in(self.store, START, END)), NOV_COUNT)

    def test_report_breakdowns_add_up(self):
        summary = report.period_summary(self.store, START, END)
        self.assertEqual(summary["by_category"], {"식비": FOOD, "교통": 12000, "간식": 10001, "미분류": 6000})
        self.assertEqual(sum(summary["by_category"].values()), NOV_TOTAL)
        paid = {name: r["paid"] for name, r in settle.balances(self.store, START, END).items()}
        self.assertEqual(summary["by_person"], paid)

    def test_category_totals_match_across_features(self):
        # 보고서의 분류 합 = 예산 상태의 지출 = 분류로 거른 내보내기 합계
        summary = report.period_summary(self.store, START, END)
        spent = budget.category_status(self.store, self.cfg, "2026-11")["식비"]["spent"]
        self.assertEqual(spent, FOOD)
        self.assertEqual(summary["by_category"]["식비"], FOOD)
        self.assertEqual(self.export_total("food.csv", "식비"), (2, FOOD))

    def test_statement_sums_to_owed(self):
        owed = queries.member_shares(self.store, START, END)
        for name in NAMES:
            with self.subTest(name=name):
                rows = settle.statement(self.store, START, END, name)
                self.assertEqual(sum(r[4] for r in rows), owed[name])

    def test_settle_up_with_minimal_transfers(self):
        rows = settle.balances(self.store, START, END)
        self.assertEqual(settle.balance_sum(rows), 0)
        for frm, to, amount in settle.minimal_transfers(rows):
            settle.record_transfer(self.store, END, frm, to, amount)
        after = settle.balances(self.store, START, END)
        self.assertEqual({name: r["balance"] for name, r in after.items()}, {name: 0 for name in NAMES})
        # 송금은 지출이 아니므로 다섯 합계는 그대로다.
        self.assert_all_equal(NOV_TOTAL)

    def test_lock_keeps_totals(self):
        settle.lock_period(self.store, START, END)
        with self.assertRaises(ValueError):
            expenses.edit_expense(self.store, self.lunch["id"], amount=1)
        with self.assertRaises(ValueError):
            expenses.delete_expense(self.store, self.lunch["id"])
        with self.assertRaises(ValueError):
            expenses.add_expense(self.store, "2026-11-28", KIM, 1000, NAMES)
        with self.assertRaises(ValueError):
            categorize.set_category(self.store, self.lunch["id"], "기타")
        categorize.add_rule(self.rules, "기타", keywords=["점심"], priority=9)
        self.assertEqual(categorize.apply_rules(self.store, self.rules), [])
        self.assert_all_equal(NOV_TOTAL)

    def test_totals_follow_later_changes(self):
        # 확정 전에 지출을 더하고 지우면 다섯 값이 함께 바뀌어야 한다.
        expenses.add_expense(self.store, "2026-11-28", PARK, 3333, [KIM, PARK], memo="택시")
        expenses.delete_expense(self.store, self.cafe["id"])
        self.assert_all_equal(NOV_TOTAL + 3333 - 10001)


if __name__ == "__main__":
    unittest.main()
