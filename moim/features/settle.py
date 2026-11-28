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
import datetime as dt
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
    # 남은 금액은 따로 계산한다(rows 는 바꾸지 않음). 목록은 rows 순서(명부 순서)를 유지한다.
    senders = [[name, -r["balance"]] for name, r in rows.items() if r["balance"] < 0]
    receivers = [[name, r["balance"]] for name, r in rows.items() if r["balance"] > 0]
    transfers = []
    while senders and receivers:
        # max 는 같은 값이면 앞의 것을 고르므로, 금액이 같으면 명부 순서가 먼저다.
        frm = max(senders, key=lambda s: s[1])
        to = max(receivers, key=lambda r: r[1])
        amount = min(frm[1], to[1])
        transfers.append((frm[0], to[0], amount))
        frm[1] -= amount
        to[1] -= amount
        senders = [s for s in senders if s[1] > 0]
        receivers = [r for r in receivers if r[1] > 0]
    return transfers


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
    if store.member(person) is None:
        raise ValueError(f"명부에 없는 사람입니다: {person}")
    # 부담액은 balances·member_shares 와 같은 expense_shares 로 계산해 내역서 합 = 그 사람의 owed 가 되게 한다.
    # 참여자인 지출만 넣는다(낸 사람이어도 참여자가 아니면 부담이 없으므로 넣지 않는다). 순서는 expenses_in(날짜 → 번호).
    rows = []
    for e in expenses_in(store, start, end):
        if person in e["members"]:
            rows.append((e["date"], e["id"], e.get("memo", ""), e["amount"], expense_shares(e)[person]))
    return rows


def exclude_member(store, eid, name):
    """특정 지출에서 특정 사람을 뺀다(그 사람 몫을 남은 사람이 나눈다)."""
    e = store.get_expense(eid)
    if e.get("deleted"):
        raise ValueError(f"삭제된 지출입니다: {e['id']}번")
    # 규약 6절: 확정한 기간의 지출은 수정할 수 없다.
    if is_locked(store, e["date"]):
        raise ValueError(f"정산이 확정된 날짜의 지출은 고칠 수 없습니다: {e['date']}")
    if name not in e["members"]:
        raise ValueError(f"{e['id']}번 지출의 참여자가 아닙니다: {name}")
    if len(e["members"]) == 1:
        raise ValueError(f"참여자가 한 명뿐이라 뺄 수 없습니다: {name}")
    # 규격 4-4 2번: members·weights 에서 빼고 수정 이력에 "exclude" 로 남긴다.
    before = copy.deepcopy(e)
    e["members"] = [m for m in e["members"] if m != name]
    if e.get("weights"):
        e["weights"] = {m: w for m, w in e["weights"].items() if m != name}
    store.record("exclude", e["id"], before, e)
    return e


def compare(old_rows, new_rows):
    """이전 정산과 비교: {이름: (이전 잔액, 지금 잔액, 차이)}"""
    # 순서: 지금 정산(명부 순서) 다음에 이전 정산에만 있는 사람. 한쪽에 없으면 잔액 0, 차이 = 지금 - 이전.
    names = list(new_rows) + [name for name in old_rows if name not in new_rows]
    result = {}
    for name in names:
        before = old_rows[name]["balance"] if name in old_rows else 0
        now = new_rows[name]["balance"] if name in new_rows else 0
        result[name] = (before, now, now - before)
    return result


def add_recurring(store, day, payer, amount, members, memo, start_month):
    """반복 지출을 등록한다. 돌려주는 값: 등록한 반복 지출(dict). 지출은 run_recurring 이 만든다."""
    if isinstance(day, bool) or not isinstance(day, int) or not 1 <= day <= 31:
        raise ValueError(f"반복 날짜는 1~31 사이의 정수여야 합니다: {day}")
    year, month = dates.parse_month(start_month)
    # run_recurring 이 dt.date 로 날짜를 만들 수 있는 연도(1~9999)만 받는다. 0년 등은 저장 전에 거부한다.
    if not dt.MINYEAR <= year <= dt.MAXYEAR:
        raise ValueError(f"시작 달의 연도가 잘못되었습니다: {start_month}")
    try:
        won = money.to_won(amount)
    except (ValueError, DecimalException, OverflowError):
        raise ValueError(f"금액 형식이 잘못되었습니다: {amount}") from None
    if won < 1:
        raise ValueError("금액은 1원 이상이어야 합니다")
    if not isinstance(members, (list, tuple)) or not members:
        raise ValueError("참여자는 한 명 이상이어야 합니다")
    if len(set(members)) != len(members):
        raise ValueError("참여자 이름이 중복되었습니다")
    # 회원 기간은 달마다 다르므로 여기서는 명부에 있는지만 본다. 기간 검사는 run_recurring 의 insert 가 한다.
    for name in [payer, *members]:
        if store.member(name) is None:
            raise ValueError(f"명부에 없는 사람입니다: {name}")
    # 규격 4-2: 반복 번호는 지출 번호(next_id)와 따로 매긴다.
    rid = max((r["id"] for r in store.data["recurring"]), default=0) + 1
    rec = {"id": rid, "day": day, "payer": payer, "amount": won, "members": list(members),
           "weights": None, "memo": memo, "start_month": f"{year:04d}-{month:02d}", "last_month": None}
    store.data["recurring"].append(rec)
    return rec


def run_recurring(store, until):
    """until 날짜까지 아직 만들지 않은 반복 지출을 만든다. 달 말일보다 큰 날은 말일로. 돌려주는 값: 만든 지출 목록."""
    return run_recurring_report(store, until)[0]


def run_recurring_report(store, until):
    """run_recurring 과 같고 건너뛴 달도 알려 준다(규격 4-4 7번). 돌려주는 값: (만든 지출 목록, [(반복 번호, 날짜, 이유)])"""
    end_day = dates.parse(until)
    end_ym = (end_day.year, end_day.month)
    created, skipped = [], []
    for rec in store.data["recurring"]:
        # 규격 4-4 3번: 이미 만든 달은 last_month 로 판단한다.
        if rec.get("last_month"):
            start_ym = dates.next_month(*dates.parse_month(rec["last_month"]))
        else:
            start_ym = dates.parse_month(rec["start_month"])
        for year, month in dates.months_between(start_ym, end_ym):
            day = dt.date(year, month, min(rec["day"], dates.days_in_month(year, month)))
            if day > end_day:
                break
            try:
                expense = ledger.insert(store, day, rec["payer"], rec["amount"], rec["members"],
                                        memo=rec.get("memo", ""), weights=rec.get("weights"),
                                        recurring_id=rec["id"])
            except ValueError as e:
                # 확정된 달이거나 그날 회원이 아닌 사람이 있으면 그달은 만들지 않고 넘어간다(규격 4-4 7번).
                expense = None
                skipped.append((rec["id"], dates.fmt(day), str(e)))
            if expense is not None:
                created.append(expense)
            rec["last_month"] = f"{year:04d}-{month:02d}"
    return created, skipped
