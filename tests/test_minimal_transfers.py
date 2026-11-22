"""기능 4: 송금 횟수를 줄인 송금 목록(minimal_transfers) 테스트."""

import copy
import unittest

from moim.features import settle


def rows_of(balances):
    """{이름: 잔액} → balances 형식의 rows(minimal_transfers 는 balance 만 쓴다)."""
    return {name: {"balance": b} for name, b in balances.items()}


class MinimalTransfers(unittest.TestCase):
    def test_skeleton_example(self):
        # 구현순서 PDF 8쪽 "정산 결과와 송금 목록"의 출력
        rows = rows_of({"김민수": -11975, "이서연": -5563, "박지훈": -44236,
                        "최유진": -112526, "정하늘": 131552, "한도윤": 42748})
        self.assertEqual(settle.minimal_transfers(rows), [
            ("최유진", "정하늘", 112526),
            ("박지훈", "한도윤", 42748),
            ("김민수", "정하늘", 11975),
            ("이서연", "정하늘", 5563),
            ("박지훈", "정하늘", 1488),
        ])

    def test_one_receiver_many_senders(self):
        rows = rows_of({"가": 900, "나": -300, "다": -600})
        self.assertEqual(settle.minimal_transfers(rows), [("다", "가", 600), ("나", "가", 300)])

    def test_tie_follows_member_order(self):
        rows = rows_of({"가": -500, "나": -500, "다": 1000})
        self.assertEqual(settle.minimal_transfers(rows), [("가", "다", 500), ("나", "다", 500)])
        rows = rows_of({"가": 500, "나": 500, "다": -1000})
        self.assertEqual(settle.minimal_transfers(rows), [("다", "가", 500), ("다", "나", 500)])

    def test_all_zero(self):
        self.assertEqual(settle.minimal_transfers(rows_of({"가": 0, "나": 0})), [])
        self.assertEqual(settle.minimal_transfers({}), [])

    def test_transfers_settle_every_balance(self):
        rows = rows_of({"가": -11975, "나": -5563, "다": -44236, "라": 61774})
        left = {name: r["balance"] for name, r in rows.items()}
        for frm, to, amount in settle.minimal_transfers(rows):
            self.assertGreater(amount, 0)
            left[frm] += amount
            left[to] -= amount
        self.assertEqual(set(left.values()), {0})

    def test_rows_unchanged(self):
        rows = rows_of({"가": 900, "나": -300, "다": -600})
        before = copy.deepcopy(rows)
        settle.minimal_transfers(rows)
        self.assertEqual(rows, before)


if __name__ == "__main__":
    unittest.main()
