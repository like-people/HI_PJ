import datetime as dt
import unittest


from moim.common.dates import month_key


class MonthKeyTests(unittest.TestCase):


    def test_date_string(self):
        self.assertEqual(month_key("2026-11-17"), "2026-11")


    def test_date_object(self):
        self.assertEqual(month_key(dt.date(2026, 11, 17)), "2026-11")


    def test_datetime_object(self):
        self.assertEqual(
            month_key(dt.datetime(2026, 11, 17, 15, 30)),
            "2026-11",
        )


    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            month_key("2026-02-30")


if __name__ == "__main__":
    unittest.main()