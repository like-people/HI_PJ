"""회비 입금 자료 항목 테스트. 담당: 기능 5(이정배)."""

import json
import tempfile
import unittest
from pathlib import Path

from moim.common.store import Store


class PaymentsDataTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "data.json"

    def test_new_store_has_empty_payments(self):
        store = Store(self.path).load()
        self.assertEqual(store.data["payments"], [])

    def test_old_file_without_payments(self):
        old_data = {
            "members": [
                {"name": "이서연", "joined": "2026-11-01", "left": None}
            ],
            "expenses": [],
            "next_id": 3,
        }
        self.path.write_text(
            json.dumps(old_data, ensure_ascii=False), encoding="utf-8"
        )
        store = Store(self.path).load()
        self.assertEqual(store.data["payments"], [])
        self.assertEqual(store.data["members"], old_data["members"])
        self.assertEqual(store.data["expenses"], old_data["expenses"])
        self.assertEqual(store.data["next_id"], 3)

    def test_payments_survive_save_and_reload(self):
        store = Store(self.path)
        payments = [
            {
                "date": "2026-11-02",
                "member": "이서연",
                "amount": 20000,
                "memo": "11월 회비",
                "source": "manual",
            },
            {
                "date": "2026-11-03",
                "member": "이서연",
                "amount": 10000,
                "memo": "",
                "source": "bank",
            },
        ]
        store.data["payments"] = payments
        store.save()
        loaded = Store(self.path).load()
        self.assertEqual(loaded.data["payments"], payments)
        self.assertEqual(loaded.data["next_id"], 1)


if __name__ == "__main__":
    unittest.main()
