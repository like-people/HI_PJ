"""기능 4: 반복 지출(add_recurring, run_recurring) 테스트."""

import unittest

from helpers import NAMES, StoreCase

from moim.common import queries
from moim.features import settle

KIM, LEE, PARK = NAMES


class AddRecurring(StoreCase):
    def test_adds_with_spec_shape(self):
        rec = settle.add_recurring(self.store, 31, KIM, "50,000", NAMES, "정기 대관료", "2026-11")
        self.assertEqual(rec, {"id": 1, "day": 31, "payer": KIM, "amount": 50000, "members": NAMES,
                               "weights": None, "memo": "정기 대관료", "start_month": "2026-11",
                               "last_month": None})
        self.assertEqual(self.store.data["recurring"], [rec])

    def test_ids_are_separate_from_expense_ids(self):
        first = settle.add_recurring(self.store, 1, KIM, 1000, NAMES, "", "2026-11")
        second = settle.add_recurring(self.store, 2, LEE, 1000, NAMES, "", "2026-11")
        self.assertEqual((first["id"], second["id"]), (1, 2))
        self.assertEqual(self.store.data["next_id"], 1)

    def test_normalizes_start_month(self):
        rec = settle.add_recurring(self.store, 5, KIM, 1000, NAMES, "", "2026-1")
        self.assertEqual(rec["start_month"], "2026-01")

    def test_rejects_bad_input(self):
        bad = [
            (0, KIM, 1000, NAMES, "2026-11"),
            (32, KIM, 1000, NAMES, "2026-11"),
            ("5", KIM, 1000, NAMES, "2026-11"),
            (5, KIM, 0, NAMES, "2026-11"),
            (5, KIM, "abc", NAMES, "2026-11"),
            (5, KIM, 1000, [], "2026-11"),
            (5, KIM, 1000, [KIM, KIM], "2026-11"),
            (5, "없는사람", 1000, NAMES, "2026-11"),
            (5, KIM, 1000, [KIM, "없는사람"], "2026-11"),
            (5, KIM, 1000, NAMES, "2026-13"),
        ]
        for day, payer, amount, members, month in bad:
            with self.subTest(day=day, payer=payer, amount=amount, members=members, month=month):
                with self.assertRaises(ValueError):
                    settle.add_recurring(self.store, day, payer, amount, members, "", month)
        self.assertEqual(self.store.data["recurring"], [])

    def test_rejects_year_out_of_range(self):
        # 0년, 10000년은 형식(YYYY-MM)은 맞지만 날짜를 만들 수 없으므로 저장 전에 거부한다.
        for month in ("0000-11", "10000-01"):
            with self.subTest(month=month):
                with self.assertRaises(ValueError):
                    settle.add_recurring(self.store, 5, KIM, 1000, NAMES, "", month)
        self.assertEqual(self.store.data["recurring"], [])

    def test_bad_year_does_not_stop_other_recurring(self):
        settle.add_recurring(self.store, 5, KIM, 1000, NAMES, "", "2026-11")
        with self.assertRaises(ValueError):
            settle.add_recurring(self.store, 5, KIM, 1000, NAMES, "", "0000-11")
        created = settle.run_recurring(self.store, "2026-11-30")
        self.assertEqual([e["date"] for e in created], ["2026-11-05"])

    def test_boundary_years_are_accepted(self):
        first = settle.add_recurring(self.store, 5, KIM, 1000, NAMES, "", "0001-01")
        last = settle.add_recurring(self.store, 5, KIM, 1000, NAMES, "", "9999-12")
        self.assertEqual((first["start_month"], last["start_month"]), ("0001-01", "9999-12"))


class RunRecurring(StoreCase):
    def dates_of(self, created):
        return [e["date"] for e in created]

    def test_day_after_month_end_uses_last_day(self):
        settle.add_recurring(self.store, 31, KIM, 30000, NAMES, "정기 대관료", "2026-11")
        created = settle.run_recurring(self.store, "2027-02-28")
        self.assertEqual(self.dates_of(created), ["2026-11-30", "2026-12-31", "2027-01-31", "2027-02-28"])

    def test_leap_year_february(self):
        settle.add_recurring(self.store, 30, KIM, 1000, NAMES, "", "2028-02")
        self.assertEqual(self.dates_of(settle.run_recurring(self.store, "2028-02-29")), ["2028-02-29"])

    def test_second_run_makes_nothing(self):
        settle.add_recurring(self.store, 10, KIM, 1000, NAMES, "", "2026-11")
        self.assertEqual(len(settle.run_recurring(self.store, "2026-12-31")), 2)
        self.assertEqual(settle.run_recurring(self.store, "2026-12-31"), [])
        self.assertEqual(self.store.data["recurring"][0]["last_month"], "2026-12")
        self.assertEqual(len(self.store.data["expenses"]), 2)

    def test_day_not_reached_yet(self):
        settle.add_recurring(self.store, 25, KIM, 1000, NAMES, "", "2026-11")
        self.assertEqual(settle.run_recurring(self.store, "2026-11-24"), [])
        self.assertIsNone(self.store.data["recurring"][0]["last_month"])
        self.assertEqual(self.dates_of(settle.run_recurring(self.store, "2026-11-25")), ["2026-11-25"])

    def test_start_month_after_until(self):
        settle.add_recurring(self.store, 1, KIM, 1000, NAMES, "", "2027-01")
        self.assertEqual(settle.run_recurring(self.store, "2026-12-31"), [])

    def test_expense_fields_and_totals(self):
        rec = settle.add_recurring(self.store, 15, KIM, 30000, NAMES, "정기 대관료", "2026-11")
        (e,) = settle.run_recurring(self.store, "2026-11-30")
        self.assertEqual((e["date"], e["payer"], e["amount"], e["members"], e["memo"], e["recurring_id"]),
                         ("2026-11-15", KIM, 30000, NAMES, "정기 대관료", rec["id"]))
        self.assertIsNone(e["weights"])
        self.assertEqual(queries.period_total(self.store, "2026-11-01", "2026-11-30"), 30000)
        self.assertEqual(self.store.data["history"][-1]["action"], "add")

    def test_several_recurring_in_registration_order(self):
        settle.add_recurring(self.store, 20, KIM, 1000, NAMES, "가", "2026-11")
        settle.add_recurring(self.store, 5, LEE, 2000, NAMES, "나", "2026-11")
        created = settle.run_recurring(self.store, "2026-11-30")
        self.assertEqual([e["memo"] for e in created], ["가", "나"])
        self.assertEqual([e["recurring_id"] for e in created], [1, 2])

    def test_locked_month_is_skipped(self):
        settle.add_recurring(self.store, 10, KIM, 1000, NAMES, "", "2026-11")
        self.store.data["locks"].append({"start": "2026-11-01", "end": "2026-11-30"})
        self.assertEqual(self.dates_of(settle.run_recurring(self.store, "2026-12-31")), ["2026-12-10"])
        self.assertEqual(self.store.data["recurring"][0]["last_month"], "2026-12")

    def test_month_with_inactive_member_is_skipped(self):
        settle.add_recurring(self.store, 10, KIM, 1000, NAMES, "", "2026-11")
        self.store.member(PARK)["left"] = "2026-11-30"
        self.assertEqual(self.dates_of(settle.run_recurring(self.store, "2026-12-31")), ["2026-11-10"])
        self.assertEqual(self.store.data["recurring"][0]["last_month"], "2026-12")


class RunRecurringReport(StoreCase):
    def test_returns_created_and_skipped(self):
        settle.add_recurring(self.store, 10, KIM, 9000, NAMES, "", "2026-11")
        self.store.data["locks"].append({"start": "2026-11-01", "end": "2026-11-30"})
        created, skipped = settle.run_recurring_report(self.store, "2026-12-31")
        self.assertEqual([e["date"] for e in created], ["2026-12-10"])
        self.assertEqual(skipped, [(1, "2026-11-10", "정산이 확정된 날짜입니다: 2026-11-10")])


if __name__ == "__main__":
    unittest.main()
