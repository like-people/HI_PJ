"""설정 파일. 팀 공동 작업 "설정 파일" 담당이 항목을 채운다.

지금은 모임 이름과 자료 파일 위치만 있다. 공고문의 설정 파일 항목(명부 파일 위치, 총무, 예산, 분류별 예산,
1인당 월 회비, 경보 비율, 분류 규칙 파일, 백업·로그 폴더)을 DEFAULT 에 더한다.
"""

import copy
import json
import os

DEFAULT = {
    "group": "우리 모임",
    "data": "data.json",
}
PATH_KEYS = ("data",)   # 설정 파일이 있는 폴더 기준으로 바꿀 경로 항목


def load(path="config.json"):
    cfg = copy.deepcopy(DEFAULT)
    base = os.path.dirname(os.path.abspath(path))
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    for key in PATH_KEYS:
        if not os.path.isabs(cfg[key]):
            cfg[key] = os.path.join(base, cfg[key])
    return cfg


def save_default(path="config.json"):
    if os.path.exists(path):
        raise FileExistsError(f"이미 있습니다: {path}")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(DEFAULT, f, ensure_ascii=False, indent=2)
