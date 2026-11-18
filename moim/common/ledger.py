"""지출 기록: 검사·추가·중복 찾기. 기능 1·6 담당이 채운다(각 함수 설명의 담당 참고)."""

from . import dates, money  # noqa: F401
from .queries import is_member_active, is_locked  # noqa: F401


def validate(store, date, payer, amount, members, weights=None):
    """지출 한 건을 검사한다. 통과하면 (date, 원 단위 금액)을 돌려주고, 아니면 이유를 담은 ValueError.
    담당: 기능 1"""
    raise NotImplementedError("기능 1 담당이 구현한다")


def duplicates(store, date, payer, amount, exclude_id=None):
    """같은 날짜·금액·사람의 지출 번호 목록(삭제된 것 제외). 담당: 기능 6"""
    target_date = dates.fmt(date)
    result = []


    for expense in store.data["expenses"]:
        if expense.get("deleted", False):
            continue


        if dates.fmt(expense["date"]) != target_date:
            continue


        if expense["payer"] != payer:
            continue


        if expense["amount"] != amount:
            continue


        if exclude_id is not None and expense["id"] == exclude_id:
            continue


        result.append(expense["id"])


    return sorted(result)


def insert(store, date, payer, amount, members, memo="", weights=None, category=None,
           recurring_id=None, action="add"):
    """검사 후 지출을 저장한다. 확정 기간이면 거부한다. 돌려주는 값: 새 지출(dict). 담당: 기능 1"""
    raise NotImplementedError("기능 1 담당이 구현한다")
