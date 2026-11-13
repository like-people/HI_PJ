import datetime
import unittest

from helpers import StoreCase

from moim.common import queries


class IsLocked(StoreCase):
    NOV = {"start": "2026-11-01", "end": "2026-11-30"}

    def test_no_locks(self):
        self.assertFalse(queries.is_locked(self.store, "2026-11-15"))

    def test_inside_and_edges(self):
        self.store.data["locks"].append(self.NOV)
        self.assertTrue(queries.is_locked(self.store, "2026-11-01"))
        self.assertTrue(queries.is_locked(self.store, "2026-11-15"))
        self.assertTrue(queries.is_locked(self.store, "2026-11-30"))

    def test_outside(self):
        self.store.data["locks"].append(self.NOV)
        self.assertFalse(queries.is_locked(self.store, "2026-10-31"))
        self.assertFalse(queries.is_locked(self.store, "2026-12-01"))

    def test_date_object(self):
        self.store.data["locks"].append(self.NOV)
        self.assertTrue(queries.is_locked(self.store, datetime.date(2026, 11, 15)))

    def test_old_data_without_locks(self):
        del self.store.data["locks"]
        self.assertFalse(queries.is_locked(self.store, "2026-11-15"))


if __name__ == "__main__":
    unittest.main()
