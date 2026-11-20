"""기능 4. 정산.

이 기능을 구현하려면 아래 공통 함수를 이 기능 담당자가 채운다(공통 모듈 병합 요청으로).
  - common/money.py split 의 비율 분배 부분(공용: 기능 5의 회비 차감)
  - common/queries.py expense_shares, member_shares — 지출별·사람별 부담액(공용: 기능 5)
  - common/queries.py is_locked — 확정 기간인가(공용: 기능 1·6)

이 기능에 필요한 자료 항목은 common/store.py 의 EMPTY 에 이 기능 담당자가 추가한다.
  - 사람별 비율(weights)
  - 송금 기록(transfers 목록)
  - 확정 기간(locks 목록)
  - 반복 지출(recurring 목록)

아래 함수의 이름과 인자는 바꾸지 않는다(인수 테스트와 채점이 이 이름으로 실행된다).
필요하면 함수를 더 만들어도 된다. 다른 기능 파일은 불러 쓰지 않는다.
"""

import copy
from decimal import DecimalException

from ..common import dates, ledger, money
from ..common.queries import expense_shares, expenses_in, is_locked, member_shares, person_paid


def balances(store, start, end):
    """사람마다 낸 돈, 부담할 돈, 이미 보낸·받은 송금, 잔액.
    잔액 = 낸 돈 - 부담할 돈 + 보낸 송금 - 받은 송금. 양수면 받을 돈, 음수면 보낼 돈."""
    paid = person_paid(store, start, end)      # {이름: 낸 돈}, 삭제 제외
    owed = member_shares(store, start, end)    # {이름: 부담할 돈}, 삭제 제외

    # 송금은 기간 안 날짜의 것만 센다. 확정 기간 날짜의 송금도 그대로 센다(규격 4-4 1번).
    sent, received = {}, {}
    for t in store.data["transfers"]:
        if dates.in_period(t["date"], start, end):
            sent[t["from"]] = sent.get(t["from"], 0) + t["amount"]
            received[t["to"]] = received.get(t["to"], 0) + t["amount"]

    # 명부 순서로, 기간 안에 낸 돈·부담·보낸 송금·받은 송금 중 하나라도 있는 사람만 넣는다.
    # 잔액이 0이어도 낸 돈이나 부담이 있으면 넣는다. 활동이 전혀 없는 사람은 넣지 않는다.
    # (person_paid·member_shares 와 같은 방식. 확정 — 김영광, 11/18)
    rows = {}
    for m in store.data["members"]:
        name = m["name"]
        row = {
            "paid": paid.get(name, 0),
            "owed": owed.get(name, 0),
            "sent": sent.get(name, 0),
            "received": received.get(name, 0),
        }
        if any(row.values()):
            row["balance"] = row["paid"] - row["owed"] + row["sent"] - row["received"]
            rows[name] = row
    return rows


def balance_sum(rows):
    """모든 사람 잔액의 합. 규칙대로라면 항상 0이다."""
    return sum(r["balance"] for r in rows.values())


def minimal_transfers(rows):
    """송금 횟수를 줄인 '누가 누구에게 얼마' 목록. 가장 많이 보낼 사람이 가장 많이 받을 사람에게 보내는 방식."""
    raise NotImplementedError("이 함수를 구현한다")


def record_transfer(store, date, frm, to, amount):
    """이미 보낸 송금을 기록한다(부분 정산)."""
    # 확정 기간 날짜의 송금도 허용한다(규격 4-4 1번). 확정은 지출만 잠근다.
    day = dates.fmt(date)
    try:
        won = money.to_won(amount)
    except (ValueError, DecimalException, OverflowError):
        raise ValueError(f"금액 형식이 잘못되었습니다: {amount}") from None
    if won < 1:
        raise ValueError("송금액은 1원 이상이어야 합니다")
    for name in (frm, to):
        if store.member(name) is None:
            raise ValueError(f"명부에 없는 사람입니다: {name}")
    if frm == to:
        raise ValueError("보내는 사람과 받는 사람이 같습니다")
    transfer = {"date": day, "from": frm, "to": to, "amount": won}
    store.data["transfers"].append(transfer)
    return transfer


def lock_period(store, start, end):
    """정산을 확정한다. 이 기간의 지출은 더 이상 추가·수정·삭제할 수 없다."""
    first, last = dates.fmt(start), dates.fmt(end)
    if first > last:
        raise ValueError(f"시작일이 끝일보다 늦습니다: {first} ~ {last}")
    # 공고문: 잔액 합이 0이 아니면 확정하지 않는다.
    total = balance_sum(balances(store, first, last))
    if total != 0:
        raise ValueError(f"잔액 합이 0이 아니어서 확정할 수 없습니다: {total}")
    # 규격 4-2: 부를 때마다 한 칸씩 추가하고 겹쳐도 합치지 않는다. 완전히 같은 기간은 다시 넣지 않는다.
    lock = {"start": first, "end": last}
    if lock not in store.data["locks"]:
        store.data["locks"].append(lock)
    return lock


def statement(store, start, end, person):
    """정산 내역서: 그 사람이 어떤 지출에 얼마를 부담했는지. [(날짜, 번호, 메모, 지출 금액, 내 부담액)]"""
    raise NotImplementedError("이 함수를 구현한다")


def exclude_member(store, eid, name):
    """특정 지출에서 특정 사람을 뺀다(그 사람 몫을 남은 사람이 나눈다)."""
    raise NotImplementedError("이 함수를 구현한다")


def compare(old_rows, new_rows):
    """이전 정산과 비교: {이름: (이전 잔액, 지금 잔액, 차이)}"""
    raise NotImplementedError("이 함수를 구현한다")


def add_recurring(store, day, payer, amount, members, memo, start_month):
    raise NotImplementedError("이 함수를 구현한다")


def run_recurring(store, until):
    """until 날짜까지 아직 만들지 않은 반복 지출을 만든다. 달 말일보다 큰 날은 말일로. 돌려주는 값: 만든 지출 목록."""
    raise NotImplementedError("이 함수를 구현한다")
