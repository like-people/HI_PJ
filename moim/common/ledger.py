"""지출 기록: 검사·추가·중복 찾기. 기능 1·6 담당이 채운다(각 함수 설명의 담당 참고)."""

from . import dates, money  # noqa: F401
from .queries import is_member_active, is_locked  # noqa: F401


def validate(store, date, payer, amount, members, weights=None):
    """지출 한 건을 검사한다. 통과하면 (date, 원 단위 금액)을 돌려주고, 아니면 이유를 담은 ValueError.
    담당: 기능 1"""
    raise NotImplementedError("기능 1 담당이 구현한다")


def duplicates(store, date, payer, amount, exclude_id=None):
    """같은 날·같은 금액·같은 사람의 지출 번호 목록(삭제된 것 제외). 담당: 기능 6"""
    raise NotImplementedError("기능 6 담당이 구현한다")


def insert(store, date, payer, amount, members, memo="", weights=None, category=None,
           recurring_id=None, action="add"):
    """검사 후 지출을 저장한다. 확정 기간이면 거부한다. 돌려주는 값: 새 지출(dict). 담당: 기능 1"""
    raise NotImplementedError("기능 1 담당이 구현한다")
