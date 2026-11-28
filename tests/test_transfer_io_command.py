import argparse
import copy
from unittest.mock import patch
import unittest
from types import SimpleNamespace
from helpers import StoreCase, NAMES
from moim.commands.transfer_io import add_parser, run
from moim.features.transfer_io import backup_all, export_csv, roundtrip_check


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


    def test_merge_command_with_real_backup_file(self):
        kim = NAMES[0]
        backup_path = self.path("other_backup.json")

        source_store = SimpleNamespace(
            data={
                "members": [
                    {
                        "name": "새회원",
                        "joined": "2026-09-01",
                        "left": None,
                    },
                    {
                        "name": "가입일누락",
                    },
                ],
                "expenses": [
                    {
                        "id": 100,
                        "date": "2026-11-10",
                        "payer": kim,
                        "amount": 3000,
                        "members": list(NAMES),
                        "memo": "병합 테스트",
                        "weights": None,
                        "category": None,
                        "deleted": False,
                    },
                    {
                        "id": 77,
                        "date": "2026-11-11",
                        "payer": kim,
                        "amount": 2000,
                        "deleted": False,
                    },
                ],
            }
        )

        # 실제 JSON 백업 파일을 만든 뒤 실제 io merge 명령으로 병합한다.
        backup_all(source_store, backup_path)

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="group")
        add_parser(sub, TransferIOCommandTests.period_args)
        args = parser.parse_args(["io", "merge", backup_path])

        output = []
        changed = run(
            args.cmd,
            args,
            self.cfg,
            self.store,
            output.append,
        )

        self.assertTrue(changed)
        self.assertIn(
            "새회원",
            [member["name"] for member in self.store.data["members"]],
        )
        self.assertEqual(len(self.store.data["expenses"]), 1)

        # 실제 병합 결과의 종류, 원본 ID, 오류 이유가 출력되는지 확인한다.
        self.assertTrue(any(
            "회원 추가 건너뜀 (가입일누락)" in line
            and "회원의 필수 항목이 없습니다" in line
            for line in output
        ))
        self.assertTrue(any(
            "원본 지출 77번 추가 건너뜀" in line
            and "필수 항목이 없습니다: members" in line
            for line in output
        ))

    def test_merge_command_returns_false_when_backup_adds_nothing(self):
        backup_path = self.path("existing_members_only.json")
        source_store = SimpleNamespace(
            data={
                "members": [
                    {
                        "name": NAMES[0],
                        "joined": "2026-09-01",
                        "left": None,
                    },
                ],
                "expenses": [],
            }
        )

        backup_all(source_store, backup_path)

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="group")
        add_parser(sub, TransferIOCommandTests.period_args)
        args = parser.parse_args(["io", "merge", backup_path])

        before = copy.deepcopy(self.store.data)
        output = []

        changed = run(
            args.cmd,
            args,
            self.cfg,
            self.store,
            output.append,
        )

        self.assertFalse(changed)
        self.assertEqual(self.store.data, before)
        self.assertTrue(any(
            "회원 0명, 지출 0건 추가" in line
            for line in output
        ))


if __name__ == "__main__":
    unittest.main()
