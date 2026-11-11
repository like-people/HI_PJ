"""테스트 공용: 임시 폴더에 자료 파일과 기본 명부를 만든다."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from moim.common.store import Store  # noqa: E402

NAMES = ["김민수", "이서연", "박지훈"]


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = Store(os.path.join(self.dir, "data.json"), os.path.join(self.dir, "backup")).load()
        for n in NAMES:
            self.store.data["members"].append({"name": n, "joined": "2026-09-01", "left": None})
        self.cfg = {"budget": {"monthly": 100000, "by_category": {"식비": 50000}},
                    "dues": {"monthly": 20000}, "warn_ratio": 0.8,
                    "rules": os.path.join(self.dir, "rules.json")}

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def path(self, name):
        return os.path.join(self.dir, name)
