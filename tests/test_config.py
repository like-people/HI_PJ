"""설정 파일 담당: 설정 읽기(config.load) 테스트. 담당: 설정 파일(백지윤).

경로 변환, 하위 항목(budget·dues) 병합, 기본값이 서로 섞이지 않는지를 확인한다.
실행: python -m unittest discover -s tests -v
"""

import json
import os
import unittest

from helpers import StoreCase

from moim.common import config


class ConfigLoad(StoreCase):
    def write(self, data):
        path = self.path("config.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return path

    def test_relative_paths_are_based_on_config_folder(self):
        path = self.write({"data": "d.json", "members_file": "m.txt", "rules": "r.json",
                           "backup_dir": "bk", "log_dir": "lg"})
        cfg = config.load(path)
        for key, name in (("data", "d.json"), ("members_file", "m.txt"), ("rules", "r.json"),
                          ("backup_dir", "bk"), ("log_dir", "lg")):
            self.assertEqual(cfg[key], os.path.join(self.dir, name))

    def test_absolute_path_is_kept(self):
        absolute = os.path.join(self.dir, "elsewhere", "r.json")
        cfg = config.load(self.write({"rules": absolute}))
        self.assertEqual(cfg["rules"], absolute)

    def test_missing_file_gives_defaults(self):
        cfg = config.load(self.path("none.json"))
        self.assertEqual(cfg["group"], "우리 모임")
        self.assertEqual(cfg["warn_ratio"], 0.8)
        self.assertEqual(cfg["rules"], os.path.join(self.dir, "rules.json"))

    def test_unset_values_are_none(self):
        cfg = config.load(self.path("none.json"))
        self.assertIsNone(cfg["treasurer"])
        self.assertIsNone(cfg["budget"]["monthly"])
        self.assertIsNone(cfg["dues"]["monthly"])

    def test_partial_budget_keeps_other_defaults(self):
        cfg = config.load(self.write({"budget": {"monthly": 100000}}))
        self.assertEqual(cfg["budget"], {"monthly": 100000, "by_category": {}})

    def test_partial_budget_by_category_only(self):
        cfg = config.load(self.write({"budget": {"by_category": {"식비": 50000}}}))
        self.assertEqual(cfg["budget"], {"monthly": None, "by_category": {"식비": 50000}})

    def test_empty_dues_keeps_default(self):
        cfg = config.load(self.write({"dues": {}}))
        self.assertEqual(cfg["dues"], {"monthly": None})

    def test_null_path_is_left_as_none(self):
        cfg = config.load(self.write({"log_dir": None}))
        self.assertIsNone(cfg["log_dir"])

    def test_defaults_are_independent_between_loads(self):
        first = config.load(self.path("none.json"))
        first["budget"]["by_category"]["식비"] = 1
        first["dues"]["monthly"] = 5
        second = config.load(self.path("none.json"))
        self.assertEqual(second["budget"]["by_category"], {})
        self.assertIsNone(second["dues"]["monthly"])
        self.assertEqual(config.DEFAULT["budget"]["by_category"], {})

    def test_example_config_matches_default_keys(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "config.example.json"), encoding="utf-8") as f:
            example = json.load(f)
        self.assertEqual(set(example), set(config.DEFAULT))


class SaveDefault(StoreCase):
    def test_writes_defaults_and_refuses_overwrite(self):
        path = self.path("config.json")
        config.save_default(path)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(json.load(f), config.DEFAULT)
        with self.assertRaises(FileExistsError):
            config.save_default(path)


if __name__ == "__main__":
    unittest.main()