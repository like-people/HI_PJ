"""지출 변경 이력의 형식과 저장 동작을 확인한다."""

import json
from datetime import datetime
from unittest.mock import patch

from helpers import StoreCase
from moim.common.store import Store


class StoreHistoryTests(StoreCase):
    def test_record_has_expected_fields_and_local_timestamp(self):
        now = datetime(2026, 11, 18, 14, 5, 30)
        expense = {"id": 3, "amount": 5000}

        with patch("moim.common.store.datetime") as clock:
            clock.now.return_value = now
            result = self.store.record("add", 3, None, expense)

        self.assertIsNone(result)
        self.assertEqual(self.store.data["history"], [{
            "at": "2026-11-18 14:05:30",
            "action": "add",
            "eid": 3,
            "before": None,
            "after": expense,
        }])

    def test_record_keeps_independent_nested_copies(self):
        before = {"members": ["김민수"]}
        after = {"members": ["이서연"]}
        self.store.record("edit", 3, before, after)

        before["members"].clear()
        after["members"].append("박지훈")

        entry = self.store.data["history"][0]
        self.assertEqual(entry["before"], {"members": ["김민수"]})
        self.assertEqual(entry["after"], {"members": ["이서연"]})

    def test_loading_old_data_adds_empty_history(self):
        with open(self.store.path, "w", encoding="utf-8") as file:
            json.dump({"members": [], "expenses": []}, file)

        reloaded = Store(self.store.path).load()
        self.assertEqual(reloaded.data["history"], [])

    def test_history_survives_save_and_reload(self):
        self.store.record("exclude", 3, {"amount": 5000}, {"amount": 5000})
        self.store.save()

        reloaded = Store(self.store.path).load()
        self.assertEqual(reloaded.data["history"], self.store.data["history"])
