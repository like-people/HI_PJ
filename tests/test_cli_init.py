"""통합 실행: `init`(기본 설정 파일 만들기) 테스트."""

import json
import os
import tempfile
import unittest

from moim.cli import main
from moim.common import config


class InitCommand(unittest.TestCase):
    def setUp(self):
        self.dir = self.enterContext(tempfile.TemporaryDirectory())
        self.config = os.path.join(self.dir, "config.json")
        self.output = []

    def init(self):
        self.output.clear()
        return main(["--config", self.config, "init"], self.output.append)

    def test_creates_default_config_only(self):
        self.assertEqual(self.init(), 0)
        self.assertEqual(self.output, [f"설정 파일을 만들었습니다: {self.config}"])
        with open(self.config, encoding="utf-8") as f:
            self.assertEqual(json.load(f), config.DEFAULT)
        self.assertEqual(os.listdir(self.dir), ["config.json"])

    def test_existing_config_is_error_and_kept(self):
        with open(self.config, "w", encoding="utf-8") as f:
            f.write('{"group": "우리 동아리"}')
        self.assertEqual(self.init(), 1)
        self.assertEqual(self.output, [f"오류: 이미 있습니다: {self.config}"])
        with open(self.config, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"group": "우리 동아리"})

    def test_created_config_works_for_other_commands(self):
        self.init()
        self.assertEqual(main(["--config", self.config, "member", "load", "--file",
                               os.path.join(self.dir, "none.txt")], self.output.append), 1)
        self.assertEqual(main(["--config", self.config, "settle", "locks"], self.output.append), 0)
        self.assertEqual(self.output[-1], "확정한 기간이 없습니다")


if __name__ == "__main__":
    unittest.main()
