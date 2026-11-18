"""조회 함수. 여러 기능이 같은 계산을 쓰므로 여기 한 곳에만 둔다. 함수마다 설명 끝에 담당 기능이 있다."""

from . import dates, money  # noqa: F401
from .rules import UNCATEGORIZED  # noqa: F401


# 담당: 기능 3(류훈태) 
def expenses_in(store, start, end, include_deleted=False):
    """기간 안의 지출 목록(시작일·끝일 포함). 담당: 기능 3"""
    found = [
        e
        for e in store.data["expenses"]
        if dates.in_period(e["date"], start, end)
        and (include_deleted or not e.get("deleted"))
    ]
    return sorted(found, key=lambda e: (e["date"], e["id"]))


def period_total(store, start, end):
    """기간 합계. 담당: 기능 6"""
    raise NotImplementedError("기능 6 담당이 구현한다")

# 담당: 기능 2(백지윤)
def category_of(e):
    """지출의 분류 이름. 분류가 없으면 규약의 "미분류". 담당: 기능 2"""
    category = e.get("category")
    if category is None or category == "":
        return UNCATEGORIZED
    return category

# 담당: 기능 2(백지윤)
def category_totals(store, start, end):
    """분류별 건수와 금액. {분류: {"count": n, "amount": 원}} 담당: 기능 2"""
    totals = {}
    for e in expenses_in(store, start, end):
        item = totals.setdefault(category_of(e), {"count": 0, "amount": 0})
        item["count"] += 1
        item["amount"] += e["amount"]
    ordered = sorted(totals.items(), key=lambda kv: (-kv[1]["amount"], kv[0]))
    return dict(ordered)


# 담당: 기능 3(류훈태)
def person_paid(store, start, end):
    """사람마다 낸 돈 합계. 담당: 기능 3"""
    paid = {}
    for e in expenses_in(store, start, end):
        paid[e["payer"]] = paid.get(e["payer"], 0) + e["amount"]
    names = [m["name"] for m in store.data["members"]]
    return {name: paid[name] for name in names if name in paid}


def is_member_active(store, name, on):
    """그날 모임 회원인가. 가입일 이상, 탈퇴일 이하(탈퇴일 당일까지는 회원). 담당: 기능 5"""
    day = dates.parse(on)
    member = store.member(name)

    if member is None:
        return False

    joined = dates.parse(member["joined"])
    left = member.get("left")

    return joined <= day and (
        left is None or day <= dates.parse(left)
    )


# 담당: 기능 5(이정배)
def active_members(store, on):
    """그날의 회원 이름 목록(명부 순서). 담당: 기능 5"""
    day = dates.parse(on)
    return [
        member["name"]
        for member in store.data["members"]
        if is_member_active(store, member["name"], day)
    ]


# 담당: 기능 4(김영광)
def expense_shares(e):
    """지출 하나의 사람별 부담액. 담당: 기능 4

    돌려주는 값: {이름: 부담액}, members 순서. 합계는 지출 금액과 같다.
    weights 가 없거나 null 이면 균등 분배(money.split). 삭제 여부는 보지 않는다(부르는 쪽이 거른다).
    """
    return money.split(e["amount"],e["members"],e["payer"],e.get("weights"))


def member_shares(store, start, end):
    """기간 동안 사람마다 부담할 돈 합계. 담당: 기능 4"""
    raise NotImplementedError("기능 4 담당이 구현한다")


# 담당: 기능 4(김영광)
def is_locked(store, on):
    """정산이 확정된 기간에 속하는 날짜인가. 담당: 기능 4

    store.data["locks"] 의 기간 가운데 하나라도 on 을 포함하면 True.
    기간은 시작일·끝일을 모두 포함한다(dates.in_period).

    locks 한 칸의 형식(settle.lock_period 가 이 모양으로 추가한다):
        {"start": "2026-11-01", "end": "2026-11-30"}   # 날짜는 "YYYY-MM-DD" 문자열
    on 은 "YYYY-MM-DD" 문자열이나 datetime.date 둘 다 된다.
    locks 항목이 없는 옛 자료 파일이면 확정 기간이 없는 것으로 본다.
    """
    return any(dates.in_period(on, lk["start"], lk["end"]) for lk in store.data.get("locks", []))
