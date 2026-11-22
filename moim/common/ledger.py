"""지출 기록: 검사·추가·중복 찾기. 기능 1·6 담당이 채운다(각 함수 설명의 담당 참고)."""

from decimal import DecimalException

from . import dates, money  # noqa: F401
from .queries import is_member_active, is_locked  # noqa: F401

#담당: 기능1(이승경)
def validate(store, date, payer, amount, members, weights=None):
    """지출 한 건을 검사한다. 통과하면 (date, 원 단위 금액)을 돌려주고, 아니면 이유를 담은 ValueError.
    담당: 기능 1"""
    day = dates.parse(date)
    try:
        won = money.to_won(amount)
    except (ValueError, DecimalException, OverflowError):
        raise ValueError(f"금액 형식이 잘못되었습니다: {amount}") from None
    if won < 1:
        raise ValueError("금액은 1원 이상이어야 합니다")

    if not isinstance(members, (list, tuple)) or not members:
        raise ValueError("참여자는 한 명 이상이어야 합니다")
    if any(not isinstance(name, str) or not name.strip() for name in members):
        raise ValueError("참여자 이름이 잘못되었습니다")
    if len(set(members)) != len(members):
        raise ValueError("참여자 이름이 중복되었습니다")

    if not is_member_active(store, payer, day):
        raise ValueError(f"지출일에 활동 중인 회원이 아닌 낸 사람입니다: {payer}")
    for name in members:
        if not is_member_active(store, name, day):
            raise ValueError(f"지출일에 활동 중인 회원이 아닌 참여자입니다: {name}")

    if weights is not None:
        if not isinstance(weights, dict) or weights.keys() != set(members):
            raise ValueError("비율의 이름은 참여자 목록과 일치해야 합니다")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1
               for value in weights.values()):
            raise ValueError("비율은 1 이상의 정수여야 합니다")

    if is_locked(store, day):
        raise ValueError(f"정산이 확정된 날짜입니다: {day.isoformat()}")
    return day.isoformat(), won



# 담당: 기능 6(류강현)
def duplicates(store, date, payer, amount, exclude_id=None):
    """같은 날짜·금액·사람의 지출 번호 목록(삭제된 것 제외). 담당: 기능 6"""
    target_date = dates.fmt(date)
    target_amount = money.to_won(amount)
    result = []

    for expense in store.data["expenses"]:
        if expense.get("deleted", False):
            continue

        if dates.fmt(expense["date"]) != target_date:
            continue

        if expense["payer"] != payer:
            continue

        if expense["amount"] != target_amount:
            continue

        if exclude_id is not None and expense["id"] == exclude_id:
            continue

        result.append(expense["id"])

    return sorted(result)

#담당: 기능1(이승경)
def insert(store, date, payer, amount, members, memo="", weights=None, category=None,
           recurring_id=None, action="add"):
    """검사 후 지출을 저장한다. 확정 기간이면 거부한다. 돌려주는 값: 새 지출(dict). 담당: 기능 1"""
    day, won = validate(store, date, payer, amount, members, weights)
    eid = store.new_id()
    expense = {
        "id": eid,
        "date": day,
        "payer": payer,
        "amount": won,
        "members": list(members),
        "memo": memo,
        "weights": None if weights is None else weights.copy(),
        "category": category,
        "recurring_id": recurring_id,
        "deleted": False,
    }
    store.data["expenses"].append(expense)
    store.record(action, eid, None, expense)
    return expense
