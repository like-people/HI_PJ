"""자료 파일 안전 저장·백업·복구 테스트. 담당: 이정배."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from moim.common.store import Store


class StoreRecoveryTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.path = self.root / "data.json"
        self.store = Store(self.path)

    def write_backup(self, stamp, content):
        directory = Path(self.store.backup_dir)
        directory.mkdir(exist_ok=True)
        path = directory / f"data.json-{stamp}.json"
        path.write_text(content, encoding="utf-8")
        return str(path)

    def test_first_save(self):
        self.store.save()
        self.assertEqual(Store(self.path).load().data, self.store.data)
        self.assertEqual(self.store.backups(), [])

    def test_backup_contains_previous_data(self):
        self.store.save()
        previous = self.path.read_bytes()
        self.store.data["next_id"] = 2
        self.store.save()
        backups = self.store.backups()
        self.assertEqual(len(backups), 1)
        self.assertEqual(Path(backups[0]).read_bytes(), previous)
        self.assertEqual(Store(self.path).load().data["next_id"], 2)

    def test_keep_latest_ten_in_order(self):
        for number in range(1, 14):
            self.store.data["next_id"] = number
            self.store.save()
        backups = self.store.backups()
        self.assertEqual(len(backups), 10)
        numbers = [
            json.loads(Path(path).read_text(encoding="utf-8"))["next_id"]
            for path in backups
        ]
        self.assertEqual(numbers, list(range(3, 13)))

    def test_ignore_unrelated_backups(self):
        own = self.write_backup(
            "20261117-120000-000001", '{"members":[],"expenses":[]}'
        )
        other = (
            Path(self.store.backup_dir)
            / "other.json-20261117-120000-000001.json"
        )
        other.write_text("{}", encoding="utf-8")
        self.assertEqual(self.store.backups(), [own])

    def test_save_failure_preserves_original(self):
        self.store.save()
        previous = self.path.read_bytes()
        self.store.data["next_id"] = 2
        with patch(
            "moim.common.store.os.replace",
            side_effect=OSError("교체 실패"),
        ):
            with self.assertRaises(OSError):
                self.store.save()
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.root.glob(".moim-*.tmp")), [])

    def test_recover_latest_and_preserve_broken(self):
        self.store.save()
        self.store.data["next_id"] = 2
        self.store.save()
        self.store.data["next_id"] = 3
        self.store.save()
        latest = self.store.backups()[-1]
        self.path.write_bytes(b"{broken")
        self.assertIs(self.store.recover(), self.store)
        self.assertEqual(self.store.recovered_from, latest)
        self.assertEqual(self.store.data["next_id"], 2)
        self.assertEqual(Store(self.path).load().data, self.store.data)
        broken = list(self.root.glob("data.json.broken-*"))
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0].read_bytes(), b"{broken")

    def test_skip_invalid_backups_and_fill_defaults(self):
        good = self.write_backup(
            "20261117-120000-000001", '{"members":[],"expenses":[]}'
        )
        self.write_backup(
            "20261117-120000-000002", '{"members":1,"expenses":[]}'
        )
        self.write_backup("20261117-120000-000003", "{broken")
        self.path.write_bytes(b"{original-broken")
        self.store.recover()
        self.assertEqual(self.store.recovered_from, good)
        self.assertEqual(self.store.data["next_id"], 1)
        self.assertEqual(self.store.data["locks"], [])

    def test_no_valid_backup_preserves_original(self):
        self.write_backup("20261117-120000-000001", "{broken")
        self.path.write_bytes(b"{original-broken")
        with self.assertRaises(ValueError):
            self.store.recover()
        self.assertEqual(self.path.read_bytes(), b"{original-broken")
        self.assertEqual(list(self.root.glob("data.json.broken-*")), [])

    def test_recover_failure_preserves_original(self):
        self.store.save()
        self.store.save()
        self.path.write_bytes(b"{broken")
        with patch(
            "moim.common.store.os.replace",
            side_effect=OSError("교체 실패"),
        ):
            with self.assertRaises(OSError):
                self.store.recover()
        self.assertEqual(self.path.read_bytes(), b"{broken")
        self.assertIsNone(self.store.recovered_from)
        self.assertEqual(list(self.root.glob(".moim-recover-*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
