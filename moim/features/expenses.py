"""기능 1. 지출 입력·관리.

이 기능을 구현하려면 아래 공통 함수를 이 기능 담당자가 채운다(공통 모듈 병합 요청으로).
  - common/ledger.py validate — 지출 한 건 검사(공용: 기능 6의 가져오기 미리 보기)
  - common/ledger.py insert — 검사 후 저장(공용: 기능 4·5·6)

이 기능에 필요한 자료 항목은 common/store.py 의 EMPTY 에 이 기능 담당자가 추가한다.
  - 지출의 삭제 표시(deleted)
  - 수정·삭제 이력(history 목록과 Store.record)

아래 함수의 이름과 인자는 바꾸지 않는다(인수 테스트와 채점이 이 이름으로 실행된다).
필요하면 함수를 더 만들어도 된다. 다른 기능 파일은 불러 쓰지 않는다.
"""

import copy
import csv
from ..common import dates, ledger, money
from ..common.queries import is_locked


def add_member(store, name, joined):
    """명부에 회원을 추가한다. 돌려주는 값: 추가한 회원 {"name", "joined", "left": None}.
    이름이 비었거나, 명령 인자의 구분자(, ; =)가 들어 있거나, 이미 명부에 있는 이름이면 ValueError."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("회원 이름이 비어 있습니다")
    name = name.strip()
    if any(ch in name for ch in ",;=:"):
        raise ValueError(f"회원 이름에 쉼표(,)·세미콜론(;)·등호(=)·콜론(:)은 쓸 수 없습니다: {name}")
    if store.member(name) is not None:
        raise ValueError(f"이미 명부에 있는 이름입니다: {name}")
    member = {"name": name, "joined": dates.fmt(joined), "left": None}
    store.data["members"].append(member)
    return member


def leave_member(store, name, left):
    """회원의 탈퇴일을 정한다(탈퇴일 당일까지 회원, 규약 4절). 돌려주는 값: 바꾼 회원(dict).
    명부에 없거나, 탈퇴일이 가입일보다 빠르거나, 탈퇴일 다음 날 이후의 지출(삭제 제외)에
    낸 사람·참여자로 들어 있으면 ValueError(자료는 그대로)."""
    member = store.member(name)
    if member is None:
        raise ValueError(f"명부에 없는 회원입니다: {name}")
    day = dates.parse(left)
    if day < dates.parse(member["joined"]):
        raise ValueError(f"탈퇴일이 가입일({member['joined']})보다 빠릅니다: {dates.fmt(day)}")
    later = sorted(
        e["id"] for e in store.data["expenses"]
        if not e.get("deleted") and dates.parse(e["date"]) > day
        and (e.get("payer") == name or name in e.get("members", []))
    )
    if later:
        ids = ", ".join(f"{eid}번" for eid in later)
        raise ValueError(f"탈퇴일 뒤의 지출에 들어 있어 탈퇴 처리할 수 없습니다: {ids}")
    member["left"] = dates.fmt(day)
    return member

# 담당: 설정 파일(백지윤)
def load_members_file(store, path):
    """명부 파일을 읽어 명부에 반영한다. 한 줄 형식: 이름,가입일[,탈퇴일]. '#' 줄과 빈 줄은 건너뛴다.
    이미 있는 사람은 탈퇴일만 반영한다. 돌려주는 값: (추가한 이름, 탈퇴 반영한 이름, [(줄 번호, 오류)])"""
    added, left_applied, errors = [], [], []    
    with open(path, encoding="utf-8-sig") as f:lines = f.read().splitlines()
    for no, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) not in (2, 3) or not parts[0] or not parts[1]:
            errors.append((no, "형식이 잘못되었습니다(이름,가입일[,탈퇴일])"))
            continue
        name = parts[0]
        try:
            joined = dates.parse(parts[1])
            left = dates.parse(parts[2]) if len(parts) == 3 and parts[2] else None
        except ValueError as e:
            errors.append((no, str(e)))
            continue
        member = store.member(name)
        start = dates.parse(member["joined"]) if member else joined
        if left is not None and left < start:
            errors.append((no, "탈퇴일이 가입일보다 빠릅니다"))
            continue
        if member is None:
            store.data["members"].append(
                {"name": name, "joined": dates.fmt(joined), "left": dates.fmt(left) if left else None})
            added.append(name)
        elif left is not None and member.get("left") != dates.fmt(left):
            # 탈퇴일 뒤 지출에 들어 있는지 등은 leave_member 가 같은 규칙으로 검사한다(기능 1 규칙)
            try:
                leave_member(store, name, dates.fmt(left))
            except ValueError as e:
                errors.append((no, str(e)))
                continue
            left_applied.append(name)
    return added, left_applied, errors


def list_members(store):
    """명부 순서의 회원 목록. 돌려주는 값: [{"name", "joined", "left"}] 사본(바꿔도 명부는 그대로)."""
    return [dict(member) for member in store.data["members"]]


def add_expense(store, date, payer, amount, members, memo="", weights=None, category=None):
    """지출을 추가한다. 돌려주는 값: (지출, 경고 목록)."""
    expense = ledger.insert(
        store, date, payer, amount, members, memo=memo, weights=weights, category=category,
    )
    return expense, []


def list_expenses(store, order="id", include_deleted=False):
    """지출을 번호순 또는 날짜순으로 돌려준다."""
    if order not in ("id", "date"):
        raise ValueError(f"정렬 기준은 id 또는 date여야 합니다: {order}")

    expenses = (
        expense for expense in store.data["expenses"]
        if include_deleted or not expense.get("deleted", False)
    )
    return sorted(expenses, key=lambda expense: (expense[order], expense["id"]))


def edit_expense(store, eid, **changes):
    """지출을 고친다. 바꿀 수 있는 항목: date, payer, amount, members, memo, weights, category."""
    expense = store.get_expense(eid)
    if is_locked(store, expense["date"]):
        raise ValueError(f"정산이 확정된 날짜의 지출은 수정할 수 없습니다: {expense['date']}")

    invalid_fields = changes.keys() - {"date", "payer", "amount", "members", "memo", "weights", "category"}
    if invalid_fields:
        raise ValueError(f"수정할 수 없는 항목입니다: {', '.join(sorted(invalid_fields))}")

    updated = {**expense, **changes}
    weights = updated.get("weights")
    updated["date"], updated["amount"] = ledger.validate(
        store, updated["date"], updated["payer"], updated["amount"], updated["members"], weights,
    )
    if "members" in changes:
        updated["members"] = list(updated["members"])
    if "weights" in changes and weights is not None:
        updated["weights"] = weights.copy()

    store.record("edit", expense["id"], expense, updated)
    expense.update(updated)
    return expense


def delete_expense(store, eid):
    """지출에 삭제 표시를 하고 변경 이력을 기록한다."""
    expense = store.get_expense(eid)
    if is_locked(store, expense["date"]):
        raise ValueError(f"정산이 확정된 날짜의 지출은 삭제할 수 없습니다: {expense['date']}")

    if not expense.get("deleted", False):
        updated = {**expense, "deleted": True}
        store.record("delete", expense["id"], expense, updated)
        expense["deleted"] = True
    return expense


def restore_expense(store, eid):
    """삭제 표시한 지출을 되살리고 변경 이력을 기록한다. 삭제되지 않은 지출이면 그대로 돌려준다.
    확정된 날짜이거나, 지금 명부로 다시 검사(ledger.validate)해 통과하지 못하면 ValueError(자료는 그대로)."""
    expense = store.get_expense(eid)
    if is_locked(store, expense["date"]):
        raise ValueError(f"정산이 확정된 날짜의 지출은 되살릴 수 없습니다: {expense['date']}")

    if expense.get("deleted", False):
        try:
            ledger.validate(store, expense["date"], expense["payer"], expense["amount"],
                            expense["members"], expense.get("weights"))
        except ValueError as exc:
            raise ValueError(f"{expense['id']}번 지출을 되살릴 수 없습니다: {exc}") from None
        updated = {**expense, "deleted": False}
        store.record("restore", expense["id"], expense, updated)
        expense["deleted"] = False
    return expense


def undo_last_edit(store, eid):
    """그 지출의 가장 최근 수정(edit)을 되돌린다. 수정 이력의 바꾸기 전 값으로 돌려놓고, 되돌린 사실도 이력에 남긴다."""
    # 되돌리기(undo) 이력 1건은 그보다 앞선 수정 1건을 이미 되돌린 것으로 센다. 그래서 여러 번 부르면 한 단계씩 뒤로 간다.
    # 그 수정에서 실제로 바뀐 항목만 되돌린다(뒤에 다른 기능이 고친 항목, 예: exclude 의 참여자는 그대로 둔다).
    expense = store.get_expense(eid)
    if expense.get("deleted", False):
        raise ValueError(f"삭제된 지출은 되돌릴 수 없습니다: {expense['id']}번")

    target, undone = None, 0
    for entry in reversed(store.data["history"]):
        if entry["eid"] != expense["id"]:
            continue
        if entry["action"] == "undo":
            undone += 1
        elif entry["action"] == "edit":
            if undone:
                undone -= 1
            else:
                target = entry
                break
    if target is None:
        raise ValueError(f"{expense['id']}번 지출에 되돌릴 수정이 없습니다")
    if is_locked(store, expense["date"]):
        raise ValueError(f"정산이 확정된 날짜의 지출은 되돌릴 수 없습니다: {expense['date']}")

    before, after = target["before"], target["after"]
    fields = ("date", "payer", "amount", "members", "memo", "weights", "category")
    restored = {**expense}
    for field in fields:
        if before.get(field) != after.get(field):
            restored[field] = copy.deepcopy(before.get(field))
    try:
        restored["date"], restored["amount"] = ledger.validate(
            store, restored["date"], restored["payer"], restored["amount"], restored["members"],
            restored.get("weights"),
        )
    except ValueError as exc:
        raise ValueError(
            f"{expense['id']}번 지출을 되돌릴 수 없습니다: {exc} "
            f"(뒤에 참여자가 바뀌어(제외 등) 이전 상태로 되돌릴 수 없습니다)"
        ) from None

    store.record("undo", expense["id"], expense, restored)
    expense.update(restored)
    return expense


def history(store, eid=None):
    """수정·삭제 이력. eid 를 주면 그 지출의 이력만."""
    # 돌려주는 값: 기록한 순서(오래된 것부터)의 이력 사본 [{"at", "action", "eid", "before", "after"}](규격 1-2)
    entries = store.data.get("history", [])
    if eid is not None:
        eid = int(eid)
        entries = [entry for entry in entries if entry["eid"] == eid]
    return copy.deepcopy(entries)


def add_from_file(store, path):
    """파일의 여러 줄을 한꺼번에 입력한다.

    한 줄 형식(쉼표 구분): 날짜,낸 사람,금액,참여자1;참여자2;...,메모
    '#' 로 시작하는 줄과 빈 줄은 건너뛴다. 돌려주는 값: (추가한 번호 목록, [(줄 번호, 오류)])
    """
    raise NotImplementedError("이 함수를 구현한다")
