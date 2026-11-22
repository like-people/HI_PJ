"""기능 4: 이전 정산과 비교(compare) 테스트."""

import copy
import unittest

from moim.features import settle


def rows_of(balances):
    """{이름: 잔액} → balances 형식의 rows(compare 는 balance 만 쓴다)."""
    return {name: {"balance": b} for name, b in balances.items()}


class Compare(unittest.TestCase):
    def test_same_people(self):
        old = rows_of({"가": 5000, "나": -2000, "다": -3000})
        new = rows_of({"가": 3000, "나": 1000, "다": -4000})
        self.assertEqual(settle.compare(old, new), {
            "가": (5000, 3000, -2000),
            "나": (-2000, 1000, 3000),
            "다": (-3000, -4000, -1000),
        })

    def test_order_follows_new_rows(self):
        old = rows_of({"다": 0, "가": 0, "나": 0})
        new = rows_of({"가": 0, "나": 0, "다": 0})
        self.assertEqual(list(settle.compare(old, new)), ["가", "나", "다"])

    def test_missing_side_is_zero(self):
        # 이전에는 없던 사람(새로 들어옴)과 지금은 없는 사람(정산 대상에서 빠짐)
        old = rows_of({"가": 1000, "나": -1000})
        new = rows_of({"가": 500, "다": -500})
        self.assertEqual(settle.compare(old, new), {
            "가": (1000, 500, -500),
            "다": (0, -500, -500),
            "나": (-1000, 0, 1000),
        })

    def test_no_change(self):
        rows = rows_of({"가": 1000, "나": -1000})
        self.assertEqual(settle.compare(rows, rows), {"가": (1000, 1000, 0), "나": (-1000, -1000, 0)})

    def test_empty(self):
        self.assertEqual(settle.compare({}, {}), {})

    def test_inputs_unchanged(self):
        old = rows_of({"가": 1000, "나": -1000})
        new = rows_of({"가": 500, "다": -500})
        before = (copy.deepcopy(old), copy.deepcopy(new))
        settle.compare(old, new)
        self.assertEqual((old, new), before)


if __name__ == "__main__":
    unittest.main()
