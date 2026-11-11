"""기능 6. 가져오기·내보내기.

이 기능을 구현하려면 아래 공통 함수를 이 기능 담당자가 채운다(공통 모듈 병합 요청으로).
  - common/ledger.py duplicates — 같은 날·같은 사람·같은 금액 지출 찾기(공용: 기능 1)
  - common/dates.py month_key — 날짜의 달 이름(공용: 기능 3)
  - common/queries.py period_total — 기간 합계(공용: 기능 3·5)
  - common/csvio.py detect_encoding, read_csv_rows — 인코딩 판별과 CSV 읽기(공용: 기능 5의 은행 거래내역 가져오기)

아래 함수의 이름과 인자는 바꾸지 않는다(인수 테스트와 채점이 이 이름으로 실행된다).
필요하면 함수를 더 만들어도 된다. 다른 기능 파일은 불러 쓰지 않는다.
"""

import csv
import copy
import json
from ..common import dates, ledger, money
from ..common.csvio import detect_encoding, read_csv_rows  # noqa: F401
from ..common.queries import active_members, expenses_in


def export_csv(store, path, start=None, end=None, category=None):
    """CSV 로 내보낸다(엑셀에서 한글이 깨지지 않게 UTF-8 BOM). 돌려주는 값: (건수, 합계)"""
    raise NotImplementedError("이 함수를 구현한다")


def export_json(store, path, start=None, end=None, category=None):
    raise NotImplementedError("이 함수를 구현한다")


def file_total(path):
    """내보낸 파일의 금액 합계와 건수."""
    raise NotImplementedError("이 함수를 구현한다")


def verify_export(store, path, start=None, end=None, category=None):
    """내보낸 파일 합계가 원래 기록 합계와 같은가. 돌려주는 값: (같은가, 파일 합계, 기록 합계)"""
    raise NotImplementedError("이 함수를 구현한다")


def roundtrip_check(store, path, start=None, end=None, category=None):
    """내보낸 파일을 다시 읽어 원래 기록과 똑같은지 대조. 다른 번호 목록을 돌려준다(비어 있으면 같음)."""
    raise NotImplementedError("이 함수를 구현한다")


def import_csv(store, path, mapping=None, encoding=None, preview=False):
    """CSV 지출을 가져온다. 돌려주는 값: {"encoding", "added": [번호], "duplicates": [줄 번호], "errors": [(줄 번호, 오류)]}
    preview=True 면 실제로 넣지 않고 검사만 한다. 이때 added 에는 들어갈 줄 번호가 담긴다."""
    raise NotImplementedError("이 함수를 구현한다")


def backup_all(store, path):
    raise NotImplementedError("이 함수를 구현한다")


def restore_all(store, path):
    raise NotImplementedError("이 함수를 구현한다")


def merge(store, other_path):
    """다른 모임 자료(백업 파일)의 회원·지출을 합친다. 지출 번호는 새로 매긴다. 돌려주는 값: 합친 지출 수"""
    raise NotImplementedError("이 함수를 구현한다")
