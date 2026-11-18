"""설정 파일. 담당: 팀 공동 작업 "설정 파일"(백지윤).

항목 이름은 docs/규격합의_기능별.md 8절에서 확정했다.
경로 항목(PATH_KEYS)은 설정 파일이 있는 폴더 기준으로 바꾼다.
"""

import copy
import json
import os

DEFAULT = {
    "group": "우리 모임",
    "data": "data.json",
    "members_file": "members.txt",
    "rules": "rules.json",
    "backup_dir": "backup",
    "log_dir": "logs",
    "treasurer": None,                                # None 은 미설정
    "budget": {"monthly": None, "by_category": {}},   # monthly None 은 미설정
    "dues": {"monthly": None},                        # monthly None 은 미설정
    "warn_ratio": 0.8,
}
PATH_KEYS = ("data", "members_file", "rules", "backup_dir", "log_dir")   # 설정 파일이 있는 폴더 기준으로 바꿀 경로 항목


def _merge(base, extra):
    """extra 의 값으로 base 를 덮어쓴다. 안쪽 dict(budget, dues)는 빠진 항목을 기본값으로 채운다."""
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load(path="config.json"):
    cfg = copy.deepcopy(DEFAULT)
    base = os.path.dirname(os.path.abspath(path))
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            _merge(cfg, json.load(f))
    for key in PATH_KEYS:
        if cfg.get(key) and not os.path.isabs(cfg[key]):
            cfg[key] = os.path.join(base, cfg[key])
    return cfg


def save_default(path="config.json"):
    if os.path.exists(path):
        raise FileExistsError(f"이미 있습니다: {path}")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(DEFAULT, f, ensure_ascii=False, indent=2)