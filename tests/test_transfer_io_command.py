import argparse
import unittest
from unittest.mock import patch

from moim.commands.transfer_io import add_parser, run


class TransferIOCommandTests(unittest.TestCase):
    def setUp(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="group")
        add_parser(sub, self.period_args)
        self.parser = parser

    @staticmethod
    def period_args(parser):
        parser.add_argument("--month")
        parser.add_argument("--start")
        parser.add_argument("--end")

    def parse(self, *args):
        return self.parser.parse_args(["io", *args])

    def test_backup_calls_backup_all(self):
        args = self.parse("backup", "backup.json")
        store = object()
        output = []

        with patch("moim.commands.transfer_io.feat.backup_all") as backup:
            changed = run(args.cmd, args, None, store, output.append)

        backup.assert_called_once_with(store, "backup.json")
        self.assertFalse(changed)

    def test_restore_calls_restore_all_and_returns_true(self):
        args = self.parse("restore", "backup.json")
        store = object()
        output = []

        with patch("moim.commands.transfer_io.feat.restore_all") as restore:
            changed = run(args.cmd, args, None, store, output.append)

        restore.assert_called_once_with(store, "backup.json")
        self.assertTrue(changed)

    def test_total_prints_count_and_sum(self):
        args = self.parse("total", "expenses.csv")
        output = []

        with patch(
            "moim.commands.transfer_io.feat.file_total",
            return_value=(3, 6000),
        ) as file_total:
            changed = run(args.cmd, args, None, None, output.append)

        file_total.assert_called_once_with("expenses.csv")
        self.assertFalse(changed)
        self.assertEqual(len(output), 1)
        self.assertIn("3", output[0])
        self.assertIn("6,000", output[0])

    def test_roundtrip_prints_success_when_no_differences(self):
        args = self.parse("roundtrip", "expenses.csv")
        output = []

        with patch(
            "moim.commands.transfer_io.feat.roundtrip_check",
            return_value=[],
        ) as roundtrip:
            changed = run(args.cmd, args, None, None, output.append)

        roundtrip.assert_called_once_with(None, "expenses.csv")
        self.assertFalse(changed)
        self.assertEqual(len(output), 1)

    def test_roundtrip_prints_different_ids(self):
        args = self.parse("roundtrip", "expenses.csv")
        output = []

        with patch(
            "moim.commands.transfer_io.feat.roundtrip_check",
            return_value=[2, 10],
        ):
            changed = run(args.cmd, args, None, None, output.append)

        self.assertFalse(changed)
        self.assertEqual(len(output), 1)
        self.assertIn("2", output[0])
        self.assertIn("10", output[0])


if __name__ == "__main__":
    unittest.main()
