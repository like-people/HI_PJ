"""기능 5: 시작·끝을 포함하는 달 목록 검사."""
import unittest

from moim.common.dates import months_between


class MonthsBetweenTests(unittest.TestCase):
    def test_same_month(self):
        self.assertEqual(months_between((2026, 11), (2026, 11)), [(2026, 11)])

    def test_multiple_months(self):
        self.assertEqual(
            months_between((2026, 9), (2026, 11)),
            [(2026, 9), (2026, 10), (2026, 11)],
        )

    def test_cross_year(self):
        self.assertEqual(
            months_between((2026, 11), (2027, 1)),
            [(2026, 11), (2026, 12), (2027, 1)],
        )

    def test_reversed_months(self):
        self.assertEqual(months_between((2026, 11), (2026, 9)), [])

    def test_reversed_years(self):
        self.assertEqual(months_between((2027, 1), (2026, 12)), [])


if __name__ == "__main__":
    unittest.main()
