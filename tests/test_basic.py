"""기본 동작 테스트(배포용). 기능마다 기본 필수 4개의 기본 동작만 확인한다.

아직 구현하지 않은 함수(NotImplementedError)를 만나면 그 테스트는 건너뜀(skipped)으로 나온다.
자기 기능의 확장 필수·선택 테스트와 경계값 테스트는 각자 tests/test_<기능>.py 에 더 쓴다.
실행: python -m unittest discover -s tests -v
"""

import functools
import json
import os
import unittest

from helpers import NAMES, StoreCase

from moim.common import money
from moim.features import budget, categorize, expenses, report, settle, transfer_io

KIM, LEE, PARK = NAMES


def basic(fn):
    @functools.wraps(fn)
    def wrapper(self):
        try:
            fn(self)
        except NotImplementedError as exc:
            self.skipTest(f"아직 구현 전: {exc}")
    return wrapper


def add(store, date, payer, amount, members=NAMES, memo="", **kw):
    return expenses.add_expense(store, date, payer, amount, list(members), memo, **kw)[0]


class GivenCommon(StoreCase):
    """스켈레톤 코드에 채워 둔 공통 함수."""

    def test_to_won(self):
        self.assertEqual(money.to_won("36,000"), 36000)

    def test_split_even(self):
        self.assertEqual(money.split(9000, NAMES), {KIM: 3000, LEE: 3000, PARK: 3000})

    def test_store_save_load(self):
        self.store.save()
        with open(self.store.path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["members"][0]["name"], KIM)


class F1Basic(StoreCase):
    @basic
    def test_add(self):
        e = add(self.store, "2026-11-12", KIM, "36,000", memo="회의 후 저녁")
        self.assertEqual((e["amount"], e["members"], e["memo"]), (36000, NAMES, "회의 후 저녁"))

    @basic
    def test_list_order(self):
        a = add(self.store, "2026-11-20", KIM, 3000)
        b = add(self.store, "2026-11-05", KIM, 6000)
        self.assertEqual([e["id"] for e in expenses.list_expenses(self.store, order="date")], [b["id"], a["id"]])

    @basic
    def test_edit_delete(self):
        e = add(self.store, "2026-11-12", KIM, 3000)
        expenses.edit_expense(self.store, e["id"], amount=6000)
        self.assertEqual(self.store.get_expense(e["id"])["amount"], 6000)
        expenses.delete_expense(self.store, e["id"])
        self.assertEqual(expenses.list_expenses(self.store), [])

    @basic
    def test_validation(self):
        for amount, members in ((-3000, NAMES), (3000, []), (3000, ["없는사람"])):
            with self.assertRaises(ValueError):
                expenses.add_expense(self.store, "2026-11-12", KIM, amount, members)


class F2Basic(StoreCase):
    @basic
    def test_keyword(self):
        rules = []
        categorize.add_rule(rules, "식비", ["저녁"])
        e = add(self.store, "2026-11-12", KIM, 9000, memo="회의 후 저녁")
        self.assertEqual(categorize.classify(e, rules), "식비")

    @basic
    def test_json_save_load(self):
        rules = []
        categorize.add_rule(rules, "교통", ["택시"])
        categorize.save_rules(self.cfg["rules"], rules)
        self.assertEqual(categorize.load_rules(self.cfg["rules"]), rules)

    @basic
    def test_rule_add_remove(self):
        rules = []
        categorize.add_rule(rules, "식비", ["저녁"])
        categorize.add_rule(rules, "교통", ["택시"])
        categorize.remove_rule(rules, 0)
        self.assertEqual([r["category"] for r in rules], ["교통"])

    @basic
    def test_uncategorized(self):
        rules = []
        categorize.add_rule(rules, "식비", ["저녁"])
        add(self.store, "2026-11-12", KIM, 9000, memo="저녁")
        b = add(self.store, "2026-11-13", KIM, 9000, memo="현수막")
        categorize.apply_rules(self.store, rules)
        self.assertEqual([e["id"] for e in categorize.uncategorized(self.store)], [b["id"]])


class F3Basic(StoreCase):
    def setUp(self):
        super().setUp()
        self.ready = True
        try:
            add(self.store, "2026-10-15", KIM, 3000, category="식비")
            add(self.store, "2026-11-12", LEE, 6000, category="식비")
            add(self.store, "2026-11-13", KIM, 9000, category="교통")
        except NotImplementedError:
            self.ready = False

    def check_ready(self):
        if not self.ready:
            self.skipTest("아직 구현 전: 지출 추가(기능 1)")

    @basic
    def test_monthly(self):
        self.check_ready()
        self.assertEqual(report.monthly_totals(self.store, "2026-11", "2026-11"), {"2026-11": 15000})

    @basic
    def test_period(self):
        self.check_ready()
        self.assertEqual(report.period_summary(self.store, "2026-11-10", "2026-11-20")["total"], 15000)

    @basic
    def test_by_category(self):
        self.check_ready()
        self.assertEqual(report.period_summary(self.store, "2026-11-10", "2026-11-20")["by_category"],
                         {"식비": 6000, "교통": 9000})

    @basic
    def test_by_person(self):
        self.check_ready()
        self.assertEqual(report.period_summary(self.store, "2026-11-10", "2026-11-20")["by_person"],
                         {LEE: 6000, KIM: 9000})


class F4Basic(StoreCase):
    S, E = "2026-11-10", "2026-11-20"

    @basic
    def test_balance(self):
        add(self.store, "2026-11-12", KIM, 9000)
        rows = settle.balances(self.store, self.S, self.E)
        self.assertEqual((rows[KIM]["paid"], rows[KIM]["owed"], rows[KIM]["balance"]), (9000, 3000, 6000))

    @basic
    def test_even_split(self):
        add(self.store, "2026-11-12", LEE, 6000)
        rows = settle.balances(self.store, self.S, self.E)
        self.assertEqual({n: r["owed"] for n, r in rows.items()}, {KIM: 2000, LEE: 2000, PARK: 2000})

    @basic
    def test_period(self):
        add(self.store, "2026-11-05", KIM, 3000)
        add(self.store, "2026-11-12", KIM, 6000)
        self.assertEqual(settle.balances(self.store, self.S, self.E)[KIM]["paid"], 6000)

    @basic
    def test_balance_sum(self):
        add(self.store, "2026-11-12", KIM, 9000)
        add(self.store, "2026-11-13", LEE, 3000)
        self.assertEqual(settle.balance_sum(settle.balances(self.store, self.S, self.E)), 0)


class F5Basic(StoreCase):
    @basic
    def test_budget_from_config(self):
        self.assertEqual(budget.month_status(self.store, self.cfg, "2026-11")["budget"], 100000)

    @basic
    def test_over_remaining(self):
        add(self.store, "2026-11-12", KIM, 30000)
        s = budget.month_status(self.store, self.cfg, "2026-11")
        self.assertEqual((s["remaining"], s["over"]), (70000, False))

    @basic
    def test_payment(self):
        p = budget.record_payment(self.store, "2026-11-02", LEE, "20,000")
        self.assertEqual((p["member"], p["amount"]), (LEE, 20000))

    @basic
    def test_treasury(self):
        budget.record_payment(self.store, "2026-11-02", KIM, 20000)
        add(self.store, "2026-11-12", KIM, 9000)
        self.assertEqual(budget.treasury_balance(self.store), 11000)


class F6Basic(StoreCase):
    def setUp(self):
        super().setUp()
        self.ready = True
        try:
            add(self.store, "2026-10-15", KIM, 3000, category="식비")
            add(self.store, "2026-11-12", LEE, 6000, category="교통")
        except NotImplementedError:
            self.ready = False

    def check_ready(self):
        if not self.ready:
            self.skipTest("아직 구현 전: 지출 추가(기능 1)")

    @basic
    def test_csv(self):
        self.check_ready()
        self.assertEqual(transfer_io.export_csv(self.store, self.path("a.csv")), (2, 9000))

    @basic
    def test_json(self):
        self.check_ready()
        self.assertEqual(transfer_io.export_json(self.store, self.path("a.json")), (2, 9000))

    @basic
    def test_select(self):
        self.check_ready()
        self.assertEqual(transfer_io.export_csv(self.store, self.path("b.csv"), category="교통"), (1, 6000))

    @basic
    def test_verify(self):
        self.check_ready()
        p = self.path("c.csv")
        transfer_io.export_csv(self.store, p)
        self.assertTrue(transfer_io.verify_export(self.store, p)[0])


if __name__ == "__main__":
    unittest.main()
