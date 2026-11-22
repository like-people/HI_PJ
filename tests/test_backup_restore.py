"""전체 자료 백업 및 복원 테스트."""


import json
import tempfile
import unittest
from pathlib import Path

from moim.common.store import Store
from moim.features.transfer_io import backup_all, restore_all


class BackupRestoreTests(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def test_backup_and_restore_all(self):
        store = Store(self.root / "data.json")
        store.data["members"] = [
            {"name": "철수", "joined": "2026-01-01", "left": None}
        ]
        store.data["expenses"] = [
            {
                "id": 1,
                "date": "2026-11-19",
                "payer": "철수",
                "amount": 1000,
                "members": ["철수"],
                "deleted": False,
            }
        ]
        store.data["next_id"] = 2
        expected = json.loads(json.dumps(store.data))

        backup_path = self.root / "backup" / "all.json"
        backup_all(store, backup_path)

        store.data["members"] = []
        store.data["expenses"] = []
        store.data["next_id"] = 1

        restore_all(store, backup_path)
        self.assertEqual(store.data, expected)

    def test_restore_all_invalid_backup(self):
        store = Store(self.root / "data.json")
        path = self.root / "invalid.json"
        path.write_text("[]", encoding="utf-8")

        with self.assertRaises(ValueError):
            restore_all(store, path)


if __name__ == "__main__":
    unittest.main()
