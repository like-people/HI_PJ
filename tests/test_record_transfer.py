"""기능 4: 이미 보낸 송금 기록(record_transfer) 테스트."""

import copy
import datetime
import unittest

from helpers import NAMES, StoreCase

from moim.features import settle

KIM, LEE, PARK = NAMES


class RecordTransfer(StoreCase):
    def test_records_transfer(self):
        t = settle.record_transfer(self.store, "2026-11-20", PARK, KIM, 3000)
        self.assertEqual(t, {"date": "2026-11-20", "from": PARK, "to": KIM, "amount": 3000})
        self.assertEqual(self.store.data["transfers"], [t])

    def test_normalizes_date_and_amount(self):
        t = settle.record_transfer(self.store, datetime.date(2026, 11, 5), LEE, KIM, "1,234.5원")
        self.assertEqual((t["date"], t["amount"]), ("2026-11-05", 1235))

    def test_keeps_order_of_records(self):
        settle.record_transfer(self.store, "2026-11-20", PARK, KIM, 3000)
        settle.record_transfer(self.store, "2026-11-10", LEE, KIM, 1000)
        self.assertEqual([t["from"] for t in self.store.data["transfers"]], [PARK, LEE])

    def test_allowed_in_locked_period(self):
        # 규격 4-4 1번: 확정은 지출만 잠그고, 확정 기간 날짜의 송금은 기록할 수 있다
        self.store.data["locks"].append({"start": "2026-11-01", "end": "2026-11-30"})
        settle.record_transfer(self.store, "2026-11-30", PARK, KIM, 3000)
        self.assertEqual(len(self.store.data["transfers"]), 1)

    def test_rejects_invalid_input(self):
        cases = [
            ("2026-02-30", PARK, KIM, 1000, "날짜"),
            ("2026-11-20", PARK, KIM, 0, "1원 이상"),
            ("2026-11-20", PARK, KIM, -500, "1원 이상"),
            ("2026-11-20", PARK, KIM, "0.4", "1원 이상"),
            ("2026-11-20", PARK, KIM, "abc", "금액"),
            ("2026-11-20", PARK, KIM, "NaN", "금액"),
            ("2026-11-20", "없는사람", KIM, 1000, "명부"),
            ("2026-11-20", PARK, "없는사람", 1000, "명부"),
            ("2026-11-20", KIM, KIM, 1000, "같습니다"),
        ]
        before = copy.deepcopy(self.store.data)
        for date, frm, to, amount, reason in cases:
            with self.subTest(date=date, frm=frm, to=to, amount=amount):
                with self.assertRaisesRegex(ValueError, reason):
                    settle.record_transfer(self.store, date, frm, to, amount)
        self.assertEqual(self.store.data, before)


if __name__ == "__main__":
    unittest.main()
