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


class Transfers(SettleCommandCase):
    def test_list_in_roster_order_when_amounts_tie(self):
        # 이서연이 9,000원을 내고 셋이 나눔 → 김·박이 3,000원씩 보냄. 금액이 같으면 명부 순서(규격 4-3)
        self.put(1, "2026-11-12", LEE, 9000)
        code, text = self.settle("transfers", "--month", "2026-11")
        self.assertEqual(code, 0)
        self.assertEqual(text.splitlines(), [f"{KIM} -> {LEE} 3,000원", f"{PARK} -> {LEE} 3,000원"])

    def test_largest_sender_first(self):
        # 김 12,000 · 이 3,000 을 셋이 나눔(각 5,000) → 잔액 김 7,000 · 이 -2,000 · 박 -5,000
        self.put(1, "2026-11-10", KIM, 12000)
        self.put(2, "2026-11-11", LEE, 3000)
        code, text = self.settle("transfers", "--start", "2026-11-01", "--end", "2026-11-30")
        self.assertEqual(code, 0)
        self.assertEqual(text.splitlines(), [f"{PARK} -> {KIM} 5,000원", f"{LEE} -> {KIM} 2,000원"])

    def test_recorded_transfer_is_subtracted(self):
        self.put(1, "2026-11-12", LEE, 9000)
        self.store.data["transfers"].append({"date": "2026-11-20", "from": PARK, "to": LEE, "amount": 3000})
        self.assertEqual(self.settle("transfers", "--month", "2026-11"), (0, f"{KIM} -> {LEE} 3,000원"))

    def test_nothing_to_send(self):
        self.assertEqual(self.settle("transfers", "--month", "2026-11"), (0, "보낼 송금이 없습니다"))

    def test_warns_when_total_is_not_zero(self):
        self.put(1, "2026-11-12", "명부에없음", 9000)
        code, text = self.settle("transfers", "--month", "2026-11")
        self.assertEqual(code, 0)
        self.assertEqual(text.splitlines()[-1], "경고: 잔액 합계가 0이 아닙니다(-9,000). 자료를 확인하십시오")

    def test_requires_period(self):
        code, text = self.settle("transfers")
        self.assertEqual(code, 1)
        self.assertTrue(text.startswith("오류: 기간을 지정하십시오"))

    def test_does_not_change_data_file(self):
        self.put(1, "2026-11-12", LEE, 9000)
        self.store.save()
        before = self.data_text()
        self.settle("transfers", "--month", "2026-11")
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


class Unknown(SettleCommandCase):
    def test_unknown_subcommand(self):
        code, text = self.settle()
        self.assertEqual((code, text), (0, "아직 만들지 않은 명령입니다: settle"))


if __name__ == "__main__":
    unittest.main()
