"""명령 묶음 settle(commands/settle.py) 테스트.

moim.cli.main 으로 명령을 직접 실행해 화면 출력, 종료 코드, 자료 파일이 바뀌지 않는지 확인한다.
"""

import json
import unittest
from unittest.mock import patch

from helpers import NAMES, StoreCase

from moim.cli import main
from moim.common.store import Store

KIM, LEE, PARK = NAMES


class SettleCommandCase(StoreCase):
    def setUp(self):
        super().setUp()
        self.config = self.path("config.json")
        with open(self.config, "w", encoding="utf-8") as f:
            json.dump({}, f)

    def put(self, eid, date, payer, amount, members=None):
        self.store.data["expenses"].append(
            {"id": eid, "date": date, "payer": payer, "amount": amount,
             "members": list(members or NAMES), "category": None, "memo": ""})

    def settle(self, *args):
        self.store.save()
        output = []
        code = main(["--config", self.config, "settle", *args], output.append)
        return code, "\n".join(output)

    def data_text(self):
        with open(self.path("data.json"), encoding="utf-8") as f:
            return f.read()


class Balance(SettleCommandCase):
    def test_table_and_total(self):
        # 10,000원을 셋이 나누고 이서연이 냄 → 김 3,333 · 이 3,334 · 박 3,333 (규약 2절)
        self.put(1, "2026-11-12", LEE, 10000)
        self.store.data["transfers"].append({"date": "2026-11-20", "from": PARK, "to": LEE, "amount": 3000})
        code, text = self.settle("balance", "--month", "2026-11")
        self.assertEqual(code, 0)
        lines = text.splitlines()
        self.assertEqual(lines[0].split(), ["이름", "낸", "돈", "부담", "보낸", "송금", "받은", "송금", "잔액"])
        self.assertEqual(lines[2].split(), [KIM, "0", "3,333", "0", "0", "-3,333"])
        self.assertEqual(lines[3].split(), [LEE, "10,000", "3,334", "0", "3,000", "3,666"])
        self.assertEqual(lines[4].split(), [PARK, "0", "3,333", "3,000", "0", "-333"])
        self.assertEqual(lines[-1], "잔액 합계: 0")

    def test_period_by_start_and_end(self):
        self.put(1, "2026-10-31", KIM, 3000)
        self.put(2, "2026-11-01", KIM, 6000)
        self.put(3, "2026-11-30", KIM, 3000)
        self.put(4, "2026-12-01", KIM, 3000)
        code, text = self.settle("balance", "--start", "2026-11-01", "--end", "2026-11-30")
        self.assertEqual(code, 0)
        self.assertIn("9,000", text.splitlines()[2])   # 김민수가 낸 돈: 11-01 + 11-30 (시작일·끝일 포함)

    def test_empty_period(self):
        code, text = self.settle("balance", "--month", "2026-11")
        self.assertEqual(code, 0)
        self.assertEqual(text.splitlines(), ["정산할 지출이 없습니다", "잔액 합계: 0"])

    def test_warns_when_total_is_not_zero(self):
        self.put(1, "2026-11-12", "명부에없음", 9000)
        code, text = self.settle("balance", "--month", "2026-11")
        self.assertEqual(code, 0)
        self.assertIn("잔액 합계: -9,000", text)
        self.assertIn("경고", text)

    def test_requires_period(self):
        code, text = self.settle("balance")
        self.assertEqual(code, 1)
        self.assertTrue(text.startswith("오류: 기간을 지정하십시오"))

    def test_does_not_change_data_file(self):
        self.put(1, "2026-11-12", LEE, 10000)
        self.store.save()
        before = self.data_text()
        self.settle("balance", "--month", "2026-11")
        self.assertEqual(self.data_text(), before)


class Lock(SettleCommandCase):
    def saved(self):
        with open(self.path("data.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_locks_month_and_saves(self):
        self.put(1, "2026-11-12", LEE, 9000)
        code, text = self.settle("lock", "--month", "2026-11")
        self.assertEqual((code, text), (0, "정산을 확정했습니다: 2026-11-01 ~ 2026-11-30"))
        self.assertEqual(self.saved()["locks"], [{"start": "2026-11-01", "end": "2026-11-30"}])

    def test_same_period_again_does_not_save(self):
        self.store.data["locks"].append({"start": "2026-11-01", "end": "2026-11-30"})
        self.store.save()
        output = []
        with patch.object(Store, "save", side_effect=AssertionError("같은 기간 재확정인데 저장함")):
            code = main(["--config", self.config, "settle", "lock", "--start", "2026-11-01",
                         "--end", "2026-11-30"], output.append)
        self.assertEqual((code, output), (0, ["이미 확정한 기간입니다: 2026-11-01 ~ 2026-11-30"]))

    def test_refuses_when_total_is_not_zero(self):
        # 명부에 없는 사람이 낸 지출은 잔액 합이 0이 아니게 만든다(규약 6절: 확정하지 않음)
        self.put(1, "2026-11-12", "명부에없음", 9000)
        code, text = self.settle("lock", "--month", "2026-11")
        self.assertEqual(code, 1)
        self.assertTrue(text.startswith("오류: 잔액 합이 0이 아니어서"))
        self.assertEqual(self.saved()["locks"], [])

    def test_requires_period(self):
        code, text = self.settle("lock")
        self.assertEqual(code, 1)
        self.assertTrue(text.startswith("오류: 기간을 지정하십시오"))


class Locks(SettleCommandCase):
    def test_empty(self):
        self.assertEqual(self.settle("locks"), (0, "확정한 기간이 없습니다"))

    def test_sorted_table(self):
        self.store.data["locks"] = [{"start": "2026-12-01", "end": "2026-12-31"},
                                    {"start": "2026-11-01", "end": "2026-11-30"}]
        code, text = self.settle("locks")
        self.assertEqual(code, 0)
        lines = text.splitlines()
        self.assertEqual(lines[0].split(), ["시작일", "끝일"])
        self.assertEqual(lines[2].split(), ["2026-11-01", "2026-11-30"])
        self.assertEqual(lines[3].split(), ["2026-12-01", "2026-12-31"])


class Transfer(SettleCommandCase):
    def test_records_and_saves(self):
        code, text = self.settle("transfer", "--date", "2026-11-20", "--from", PARK, "--to", LEE,
                                 "--amount", "3,000")
        self.assertEqual((code, text), (0, f"송금을 기록했습니다: 2026-11-20 {PARK} → {LEE} 3,000원"))
        with open(self.path("data.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["transfers"],
                             [{"date": "2026-11-20", "from": PARK, "to": LEE, "amount": 3000}])

    def test_shows_in_balance(self):
        self.put(1, "2026-11-12", LEE, 9000)
        self.settle("transfer", "--date", "2026-11-20", "--from", PARK, "--to", LEE, "--amount", "3000")
        self.store = Store(self.path("data.json")).load()   # settle() 이 self.store 를 다시 저장하므로 명령이 저장한 자료로 바꾼다
        code, text = self.settle("balance", "--month", "2026-11")
        self.assertEqual(text.splitlines()[4].split(), [PARK, "0", "3,000", "3,000", "0", "0"])

    def test_rejects_bad_input_without_saving(self):
        self.store.save()
        before = self.data_text()
        for args in (["--from", PARK, "--to", PARK, "--amount", "1000"],
                     ["--from", "명부에없음", "--to", LEE, "--amount", "1000"],
                     ["--from", PARK, "--to", LEE, "--amount", "0"]):
            with self.subTest(args=args):
                code, text = self.settle("transfer", "--date", "2026-11-20", *args)
                self.assertEqual(code, 1)
                self.assertTrue(text.startswith("오류: "))
                self.assertEqual(self.data_text(), before)


class Recurring(SettleCommandCase):
    def rec(self, day=31, start="2026-11", rid=1, last=None):
        self.store.data["recurring"].append(
            {"id": rid, "day": day, "payer": KIM, "amount": 50000, "members": list(NAMES), "weights": None,
             "memo": "정기 대관료", "start_month": start, "last_month": last})

    def saved(self):
        with open(self.path("data.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_add_saves(self):
        code, text = self.settle("add-recurring", "--day", "31", "--payer", KIM, "--amount", "50,000",
                                 "--members", ";".join(NAMES), "--memo", "정기 대관료", "--start-month", "2026-11")
        self.assertEqual((code, text), (0, f"반복 지출을 등록했습니다: 1번 매월 31일 {KIM} 50,000원 (2026-11부터)"))
        self.assertEqual(self.saved()["recurring"][0]["members"], NAMES)

    def test_add_rejects_bad_input_without_saving(self):
        self.store.save()
        before = self.data_text()
        for args in (["--day", "32", "--payer", KIM], ["--day", "5", "--payer", "명부에없음"]):
            with self.subTest(args=args):
                code, text = self.settle("add-recurring", *args, "--amount", "1000", "--members", KIM,
                                         "--start-month", "2026-11")
                self.assertEqual(code, 1)
                self.assertTrue(text.startswith("오류: "))
                self.assertEqual(self.data_text(), before)

    def test_run_uses_last_day_of_short_months(self):
        # 31일 반복 → 11-30, 12-31, 01-31, 02-28 (공고문: 그달에 없는 날은 말일로)
        self.rec()
        code, text = self.settle("run-recurring", "--until", "2027-02-28")
        self.assertEqual(code, 0)
        self.assertEqual(text.splitlines(), [f"지출을 만들었습니다: {i}번 {d} {KIM} 50,000원 정기 대관료" for i, d in
                                             enumerate(["2026-11-30", "2026-12-31", "2027-01-31", "2027-02-28"], 1)])
        data = self.saved()
        self.assertEqual([e["recurring_id"] for e in data["expenses"]], [1, 1, 1, 1])
        self.assertEqual(data["recurring"][0]["last_month"], "2027-02")

    def test_run_again_makes_nothing_and_does_not_save(self):
        self.rec(last="2027-02")
        self.store.save()
        output = []
        with patch.object(Store, "save", side_effect=AssertionError("만든 것이 없는데 저장함")):
            code = main(["--config", self.config, "settle", "run-recurring", "--until", "2027-02-28"], output.append)
        self.assertEqual((code, output), (0, ["2027-02-28까지 새로 만들 반복 지출이 없습니다"]))

    def test_run_skips_locked_month_and_reports(self):
        # 규격 4-4 7번: 확정된 달은 건너뛰고 알리며, last_month 는 넘긴다
        self.rec()
        self.store.data["locks"].append({"start": "2026-12-01", "end": "2026-12-31"})
        code, text = self.settle("run-recurring", "--until", "2027-01-31")
        lines = text.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn("2026-11-30", lines[0])
        self.assertIn("2027-01-31", lines[1])
        self.assertEqual(lines[2], "건너뜀: 반복 1번 2026-12-31 (정산이 확정된 날짜입니다: 2026-12-31)")
        data = self.saved()
        self.assertEqual([e["date"] for e in data["expenses"]], ["2026-11-30", "2027-01-31"])
        self.assertEqual(data["recurring"][0]["last_month"], "2027-01")

    def test_run_waits_until_the_day(self):
        # 11-15 까지면 11-30 은 아직 만들지 않는다
        self.rec()
        self.assertEqual(self.settle("run-recurring", "--until", "2026-11-15"),
                         (0, "2026-11-15까지 새로 만들 반복 지출이 없습니다"))
        self.assertIsNone(self.saved()["recurring"][0]["last_month"])

    def test_list(self):
        self.assertEqual(self.settle("recurring"), (0, "등록한 반복 지출이 없습니다"))
        self.rec(last="2026-12")
        code, text = self.settle("recurring")
        lines = text.splitlines()
        self.assertEqual(lines[0].split(), ["번호", "매월", "낸", "사람", "금액", "참여자", "메모", "시작", "달",
                                            "마지막으로", "만든", "달"])
        self.assertEqual(lines[2].split(), ["1", "31일", KIM, "50,000", ";".join(NAMES), "정기", "대관료",
                                            "2026-11", "2026-12"])


class Unknown(SettleCommandCase):
    def test_unknown_subcommand(self):
        code, text = self.settle()
        self.assertEqual((code, text), (0, "아직 만들지 않은 명령입니다: settle"))


if __name__ == "__main__":
    unittest.main()
