"""자료 파일 저장. 모든 기능이 이 한 곳의 자료(store.data)를 읽고 쓴다.

자료 구조(EMPTY)는 최소 항목만 들어 있다. 기능에 필요한 항목은 그 기능 담당자가 EMPTY 에 추가한다.
옛 자료 파일에 새 항목이 없으면 읽을 때 기본값으로 채운다.
save·backups·recover 는 팀 공동 작업 "자료 파일 손상 대응" 담당이 완성한다.
"""

import copy
import json
import os
import re
import shutil
import tempfile
from datetime import datetime

EMPTY = {
    "members": [],      # {"name", "joined", "left"}
    "expenses": [],     # {"id", "date", "payer", "amount", "members", "category", "memo"}
    "next_id": 1,
    "locks": [],        # 기능 4: 확정 기간 {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
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

    # 담당: 자료 파일 손상 대응(이정배)
    def save(self):
        """임시 파일에 저장하고, 직전 정상 자료를 백업한 뒤 원본을 교체한다."""
        if isinstance(self.keep, bool) or not isinstance(self.keep, int) or self.keep < 1:
            raise ValueError("백업 보관 개수는 1 이상의 정수여야 합니다")

        self._check_shape(self.data)
        directory = os.path.dirname(os.path.abspath(self.path))
        temp_path = None

        try:
            # 원본과 같은 폴더에 써야 os.replace로 안전하게 교체할 수 있다.
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=directory,
                prefix=".moim-",
                suffix=".tmp",
                delete=False,
            ) as f:
                temp_path = f.name
                json.dump(self.data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())

            if os.path.exists(self.path):
                # 손상된 원본으로 정상 백업을 밀어내지 않도록 먼저 검사한다.
                with open(self.path, encoding="utf-8") as f:
                    previous = json.load(f)
                self._check_shape(previous)

                os.makedirs(self.backup_dir, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                prefix = f"{os.path.basename(self.path)}-{stamp}-"
                backup_path = None

                try:
                    with tempfile.NamedTemporaryFile(
                        mode="wb",
                        dir=self.backup_dir,
                        prefix=prefix,
                        suffix=".json",
                        delete=False,
                    ) as backup:
                        backup_path = backup.name
                        with open(self.path, "rb") as source:
                            shutil.copyfileobj(source, backup)
                        backup.flush()
                        os.fsync(backup.fileno())
                except BaseException:
                    if backup_path is not None:
                        os.remove(backup_path)
                    raise

            os.replace(temp_path, self.path)
            temp_path = None

            # 원본 교체가 성공한 뒤 오래된 백업을 정리한다.
            for path in self.backups()[:-self.keep]:
                os.remove(path)
        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.remove(temp_path)

    # 담당: 자료 파일 손상 대응(이정배)
    def backups(self):
        """이 자료 파일의 백업 경로를 오래된 순서로 반환한다."""
        if not os.path.isdir(self.backup_dir):
            return []

        filename = re.escape(os.path.basename(self.path))
        pattern = re.compile(
            rf"{filename}-\d{{8}}-\d{{6}}-\d{{6}}(?:-[^.]+)?\.json"
        )

        return [
            os.path.join(self.backup_dir, name)
            for name in sorted(os.listdir(self.backup_dir))
            if pattern.fullmatch(name)
            and os.path.isfile(os.path.join(self.backup_dir, name))
        ]

    # 담당: 자료 파일 손상 대응(이정배)
    def recover(self):
        """손상 원본을 보존하고 최신 정상 백업으로 복구한 뒤 자신을 반환한다."""
        restored = None
        recovered_path = None

        for path in reversed(self.backups()):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                self._check_shape(data)
            except (OSError, ValueError):
                continue
            restored = data
            recovered_path = path
            break

        if recovered_path is None:
            raise ValueError("복구할 수 있는 정상 백업이 없습니다")

        directory = os.path.dirname(os.path.abspath(self.path))
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=directory,
                prefix=".moim-recover-",
                suffix=".tmp",
                delete=False,
            ) as f:
                temp_path = f.name
                json.dump(restored, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # 손상 원본을 옆에 별도 보관하고 백업 목록과 구분한다.
            if os.path.exists(self.path):
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                broken_path = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="wb",
                        dir=directory,
                        prefix=f"{os.path.basename(self.path)}.broken-{stamp}-",
                        delete=False,
                    ) as broken:
                        broken_path = broken.name
                        with open(self.path, "rb") as source:
                            shutil.copyfileobj(source, broken)
                        broken.flush()
                        os.fsync(broken.fileno())
                except BaseException:
                    if broken_path is not None:
                        os.remove(broken_path)
                    raise

            os.replace(temp_path, self.path)
            temp_path = None
        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.remove(temp_path)

        self.data = restored
        self.recovered_from = recovered_path
        return self

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
