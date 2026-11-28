import csv
import argparse
from unittest.mock import patch
import unittest
from types import SimpleNamespace
from helpers import StoreCase, NAMES
from moim.commands.transfer_io import add_parser, run
from moim.features.transfer_io import export_csv, roundtrip_check


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

    def test_import_parser_accepts_file_and_preview(self):
        args = self.parse("import", "expenses.csv")
        self.assertEqual(args.file, "expenses.csv")
        self.assertFalse(args.preview)

        preview_args = self.parse(
            "import", "expenses.csv", "--preview"
        )
        self.assertTrue(preview_args.preview)

        mapped_args = self.parse(
            "import",
            "expenses.csv",
            "--map", "날짜=date",
            "--map", "낸 사람=payer",
        )
        self.assertEqual(
            mapped_args.map,
            ["날짜=date", "낸 사람=payer"],
        )

    def test_import_calls_import_csv_and_returns_true_when_added(self):
        args = self.parse("import", "expenses.csv")
        store = object()
        output = []

        result = {
            "encoding": "utf-8-sig",
            "added": [1],
            "duplicates": [3],
            "errors": [(4, "금액 오류")],
        }

        with patch(
            "moim.commands.transfer_io.feat.import_csv",
            return_value=result,
        ) as import_csv:
            changed = run(args.cmd, args, None, store, output.append)

        import_csv.assert_called_once_with(
            store,
            "expenses.csv",
            mapping=None,
            preview=False,
        )
        self.assertTrue(changed)
        self.assertIn("추가 1건", output[0])
        self.assertIn("중복 1건", output[0])
        self.assertIn("오류 1줄", output[0])
        self.assertIn("중복 의심 줄: 3", output)
        self.assertIn("4번째 줄: 금액 오류", output)

    def test_import_preview_does_not_return_true(self):
        args = self.parse("import", "expenses.csv", "--preview")
        store = object()
        output = []

        result = {
            "encoding": "utf-8-sig",
            "added": [1],
            "duplicates": [],
            "errors": [],
        }

        with patch(
            "moim.commands.transfer_io.feat.import_csv",
            return_value=result,
        ) as import_csv:
            changed = run(args.cmd, args, None, store, output.append)

        import_csv.assert_called_once_with(
            store,
            "expenses.csv",
            mapping=None,
            preview=True,
        )

        self.assertFalse(changed)
        self.assertIn("미리보기", output[0])
        self.assertIn(
            "미리보기이므로 실제 자료는 변경하지 않았습니다.",
            output,
        )

    def test_import_returns_false_when_nothing_added(self):
        args = self.parse("import", "expenses.csv")
        output = []

        result = {
            "encoding": "cp949",
            "added": [],
            "duplicates": [2],
            "errors": [(3, "날짜 오류")],
        }

        with patch(
            "moim.commands.transfer_io.feat.import_csv",
            return_value=result,
        ):
            changed = run(args.cmd, args, None, object(), output.append)

        self.assertFalse(changed)

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
        self.assertEqual(len(output), 2)
        self.assertIn("복원했습니다", output[0])
        self.assertIn("현재 자료를 교체", output[1])

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

        roundtrip.assert_called_once_with(
            None, "expenses.csv", None, None, None
        )
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

    def test_roundtrip_accepts_period_and_category_options(self):
        args = self.parse(
            "roundtrip",
            "expenses.csv",
            "--month",
            "2026-11",
            "--category",
            "식비",
        )
        output = []

        with patch(
            "moim.commands.transfer_io._range",
            return_value=("2026-11-01", "2026-11-30"),
        ), patch(
            "moim.commands.transfer_io.feat.roundtrip_check",
            return_value=[],
        ) as roundtrip:
            changed = run(args.cmd, args, None, None, output.append)

        roundtrip.assert_called_once_with(
            None,
            "expenses.csv",
            "2026-11-01",
            "2026-11-30",
            "식비",
        )
        self.assertFalse(changed)
        self.assertEqual(len(output), 1)

    def test_range_rejects_start_after_end(self):
        args = self.parse(
            "export",
            "expenses.csv",
            "--start",
            "2026-11-30",
            "--end",
            "2026-11-01",
        )

        with self.assertRaisesRegex(ValueError, "시작일이 끝일보다 늦습니다"):
            run(args.cmd, args, None, None, lambda message: None)

    def test_merge_parser_accepts_backup_file(self):
        args = self.parse("merge", "other_backup.json")

        self.assertEqual(args.cmd, "merge")
        self.assertEqual(args.file, "other_backup.json")

    def test_merge_reports_result_and_returns_true(self):
        args = self.parse("merge", "other_backup.json")
        store = SimpleNamespace(
            data={
                "members": [{"name": "기존회원"}],
                "expenses": [],
            }
        )
        output = []

        def fake_merge(target, path, report):
            target.data["members"].append({"name": "새회원"})
            target.data["expenses"].append({"id": 1})

            report["skipped"] = [
                {
                    "kind": "member",
                    "id": "잘못된회원",
                    "reason": "가입일이 없습니다",
                },
                {
                    "kind": "expense",
                    "id": 77,
                    "reason": "활동 회원이 아닙니다",
                },
            ]
            report["duplicates"] = [
                {"id": 88, "matches": [1]},
            ]
            return 1

        with patch(
            "moim.commands.transfer_io.feat.merge",
            side_effect=fake_merge,
        ) as merge:
            changed = run(args.cmd, args, None, store, output.append)

        merge.assert_called_once()
        self.assertEqual(merge.call_args.args[0], store)
        self.assertEqual(merge.call_args.args[1], "other_backup.json")
        self.assertIn("report", merge.call_args.kwargs)

        self.assertTrue(changed)
        self.assertTrue(any("회원 1명, 지출 1건 추가" in line for line in output))
        self.assertTrue(any("잘못된회원" in line for line in output))
        self.assertTrue(any("원본 지출 77번" in line for line in output))
        self.assertTrue(any("중복 의심 지출 1건" in line for line in output))
        self.assertTrue(any("88" in line for line in output))

    def test_merge_returns_true_when_only_members_are_added(self):
        args = self.parse("merge", "other_backup.json")
        store = SimpleNamespace(
            data={
                "members": [{"name": "기존회원"}],
                "expenses": [],
            }
        )
        output = []

        def fake_merge(target, path, report):
            target.data["members"].append({"name": "새회원"})
            report["skipped"] = []
            report["duplicates"] = []
            return 0

        with patch(
            "moim.commands.transfer_io.feat.merge",
            side_effect=fake_merge,
        ):
            changed = run(args.cmd, args, None, store, output.append)

        self.assertTrue(changed)
        self.assertTrue(any("회원 1명, 지출 0건 추가" in line for line in output))


class RoundtripIntegrationTests(StoreCase):
    def add_expense(
        self, eid, date, payer, amount, members,
        weights=None, category=None, memo="",
    ):
        self.store.data["expenses"].append({
            "id": eid,
            "date": date,
            "payer": payer,
            "amount": amount,
            "members": list(members),
            "weights": weights,
            "category": category,
            "memo": memo,
            "deleted": False,
        })

    def test_exported_csv_roundtrip_matches_real_records(self):
        kim, lee, park = NAMES

        self.add_expense(
            1, "2026-11-10", kim, 3000, NAMES,
            category="식비",
            memo="점심",
        )
        self.add_expense(
            2, "2026-11-11", lee, 6000, NAMES,
            category="교통",
            memo="택시",
        )
        self.add_expense(
            3, "2026-10-20", park, 5000, NAMES,
            category="식비",
            memo="지난달",
        )

        path = self.path("nov.csv")

        export_csv(
            self.store,
            path,
            start="2026-11-01",
            end="2026-11-30",
        )

        different = roundtrip_check(
            self.store,
            path,
            start="2026-11-01",
            end="2026-11-30",
        )

        self.assertEqual(different, [])

    def test_filtered_export_roundtrip_matches_category(self):
        kim, lee, park = NAMES

        self.add_expense(
            1, "2026-11-10", kim, 3000, NAMES,
            category="식비",
        )
        self.add_expense(
            2, "2026-11-11", lee, 6000, NAMES,
            category="교통",
        )

        path = self.path("food.csv")

        export_csv(
            self.store,
            path,
            start="2026-11-01",
            end="2026-11-30",
            category="식비",
        )

        different = roundtrip_check(
            self.store,
            path,
            start="2026-11-01",
            end="2026-11-30",
            category="식비",
        )

        self.assertEqual(different, [])

    def test_import_command_with_korean_column_mapping(self):
        kim, lee, park = NAMES
        path = self.path("mapped.csv")

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["날짜", "낸 사람", "금액", "참여자"],
            )
            writer.writeheader()
            writer.writerow({
                "날짜": "2026-11-10",
                "낸 사람": kim,
                "금액": "3000",
                "참여자": ";".join(NAMES),
            })

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="group")
        add_parser(sub, TransferIOCommandTests.period_args)

        args = parser.parse_args([
            "io",
            "import",
            path,
            "--map", "날짜=date",
            "--map", "낸 사람=payer",
            "--map", "금액=amount",
            "--map", "참여자=members",
        ])

        output = []
        changed = run(args.cmd, args, self.cfg, self.store, output.append)

        self.assertTrue(changed)
        self.assertEqual(len(self.store.data["expenses"]), 1)

        expense = self.store.data["expenses"][0]
        self.assertEqual(expense["date"], "2026-11-10")
        self.assertEqual(expense["payer"], kim)
        self.assertEqual(expense["amount"], 3000)
        self.assertEqual(expense["members"], NAMES)
        self.assertIn("추가 1건", output[0])
        self.assertIn("오류 0줄", output[0])


if __name__ == "__main__":
    unittest.main()
