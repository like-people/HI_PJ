"""자료 파일 저장. 모든 기능이 이 한 곳의 자료(store.data)를 읽고 쓴다.

자료 구조(EMPTY)는 최소 항목만 들어 있다. 기능에 필요한 항목은 그 기능 담당자가 EMPTY 에 추가한다.
옛 자료 파일에 새 항목이 없으면 읽을 때 기본값으로 채운다.
save·backups·recover 는 팀 공동 작업 "자료 파일 손상 대응" 담당이 완성한다.
"""

import copy
import json
import os

EMPTY = {
    "members": [],      # {"name", "joined", "left"}
    "expenses": [],     # {"id", "date", "payer", "amount", "members", "category", "memo"}
    "next_id": 1,
}


class Store:
    def __init__(self, path, backup_dir=None, keep=10):
        self.path = path
        self.backup_dir = backup_dir or os.path.join(os.path.dirname(os.path.abspath(path)), "backup")
        self.keep = keep
        self.data = copy.deepcopy(EMPTY)
        self.recovered_from = None

    def load(self):
        if not os.path.exists(self.path):
            self.data = copy.deepcopy(EMPTY)
            return self
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self._check_shape(data)
        self.data = data
        return self

    @staticmethod
    def _check_shape(data):
        """members·expenses 는 꼭 있어야 한다. 나중에 추가된 항목이 없는 옛 파일은 기본값으로 채운다."""
        if not isinstance(data, dict):
            raise ValueError("자료 파일 형식이 아닙니다")
        for key in ("members", "expenses"):
            if not isinstance(data.get(key), list):
                raise ValueError(f"자료 파일에 {key} 항목이 없습니다")
        for key, value in EMPTY.items():
            data.setdefault(key, copy.deepcopy(value))

    def save(self):
        """지금은 그냥 덮어쓴다. 저장 도중 멈추면 파일이 깨질 수 있다(자료 파일 손상 대응 담당이 고친다)."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def backups(self):
        """백업 파일 목록(오래된 것부터)."""
        raise NotImplementedError("자료 파일 손상 대응 담당이 구현한다")

    def recover(self):
        """깨진 파일을 옆에 남기고 마지막 정상 백업을 불러온다. 불러온 백업 경로를 recovered_from 에 둔다."""
        raise NotImplementedError("자료 파일 손상 대응 담당이 구현한다")

    def new_id(self):
        eid = self.data["next_id"]
        self.data["next_id"] += 1
        return eid

    def get_expense(self, eid):
        for e in self.data["expenses"]:
            if e["id"] == int(eid):
                return e
        raise ValueError(f"{eid}번 지출이 없습니다")

    def member(self, name):
        for m in self.data["members"]:
            if m["name"] == name:
                return m
        return None
