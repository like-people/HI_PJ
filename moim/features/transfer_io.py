
"""기능 6. 가져오기·내보내기.

공통 함수 담당: 기능 6(류강현)
다른 기능 파일은 불러 쓰지 않는다.
"""

import csv
import copy
import json
import os

from ..common import dates, ledger, money
from ..common.csvio import detect_encoding, read_csv_rows
from ..common.queries import active_members, expenses_in


CSV_FIELDS = [
    "id",
    "date",
    "payer",
    "amount",
    "members",
    "memo",
    "category",
    "weights",
]

# 파일에 자주 사용되는 열 이름도 인식한다.
FIELD_ALIASES = {
    "날짜": "date",
    "거래일자": "date",
    "일자": "date",
    "낸 사람": "payer",
    "낸사람": "payer",
    "결제자": "payer",
    "금액": "amount",
    "지출액": "amount",
    "참여자": "members",
    "참여자목록": "members",
    "메모": "memo",
    "내용": "memo",
    "분류": "category",
    "비율": "weights",
}


def _selected_expenses(store, start=None, end=None, category=None):
    """조건에 맞는 삭제되지 않은 지출을 반환한다."""
    if start is not None:
        start = dates.fmt(start)
    if end is not None:
        end = dates.fmt(end)

    if start is not None and end is not None:
        if dates.parse(start) > dates.parse(end):
            raise ValueError("시작일은 종료일보다 늦을 수 없습니다")
        expenses = expenses_in(store, start, end)
    else:
        expenses = list(store.data.get("expenses", []))

    result = []

    for expense in expenses:
        if expense.get("deleted", False):
            continue

        expense_date = dates.fmt(expense["date"])

        if start is not None and expense_date < start:
            continue
        if end is not None and expense_date > end:
            continue
        if category is not None and expense.get("category") != category:
            continue

        result.append(expense)

    return sorted(
        result,
        key=lambda e: (dates.fmt(e["date"]), e["id"])
    )


def _expense_to_csv_row(expense):
    """지출 한 건을 CSV 행으로 바꾼다."""
    return {
        "id": expense.get("id", ""),
        "date": dates.fmt(expense["date"]),
        "payer": expense["payer"],
        "amount": money.to_won(expense["amount"]),
        "members": ";".join(expense.get("members", [])),
        "memo": expense.get("memo", ""),
        "category": expense.get("category") or "",
        "weights": json.dumps(
            expense.get("weights"),
            ensure_ascii=False
        ),
    }


def _row_to_expense(row):
    """CSV 행을 지출 입력 자료로 변환한다."""
    normalized = {}

    for key, value in row.items():
        if key is None:
            continue

        key = str(key).strip()
        normalized[key] = value.strip() if isinstance(value, str) else value

    # 한글 열 이름을 내부 필드 이름으로 변환한다.
    for alias, field in FIELD_ALIASES.items():
        if alias in normalized and field not in normalized:
            normalized[field] = normalized[alias]

    required = ("date", "payer", "amount")
    for field in required:
        if not normalized.get(field):
            raise ValueError(f"{field} 값이 없습니다")

    members_value = normalized.get("members", "")

    if isinstance(members_value, list):
        members = members_value
    elif members_value:
        try:
            parsed = json.loads(members_value)
            members = parsed if isinstance(parsed, list) else None
        except (ValueError, TypeError):
            members = None

        if members is None:
            members = members_value.split(";")
    else:
        members = []

    members = [str(name).strip() for name in members if str(name).strip()]

    weights_value = normalized.get("weights")
    weights = None

    if weights_value:
        if isinstance(weights_value, dict):
            weights = weights_value
        else:
            try:
                weights = json.loads(weights_value)
            except (ValueError, TypeError):
                raise ValueError("비율(weights) 형식이 잘못되었습니다") from None

        if weights is not None and not isinstance(weights, dict):
            raise ValueError("비율(weights)은 객체 형식이어야 합니다")

    return {
        "date": normalized["date"],
        "payer": normalized["payer"],
        "amount": normalized["amount"],
        "members": members,
        "memo": normalized.get("memo", ""),
        "category": normalized.get("category") or None,
        "weights": weights,
    }


def _read_export(path):
    """내보낸 CSV 또는 JSON 파일을 읽는다."""
    with open(path, "r", encoding="utf-8-sig") as file:
        first = file.read(1)

    if first in ("[", "{"):
        with open(path, "r", encoding="utf-8-sig") as file:
            data = json.load(file)

        if isinstance(data, dict):
            rows = data.get("expenses")
            if not isinstance(rows, list):
                raise ValueError("JSON 파일에 expenses 목록이 없습니다")
        elif isinstance(data, list):
            rows = data
        else:
            raise ValueError("JSON 파일 형식이 잘못되었습니다")

        return rows

    _, rows = read_csv_rows(path)
    return [row for _, row in rows]


def _record_total(expenses):
    return sum(money.to_won(e["amount"]) for e in expenses)


def _expense_signature(date, payer, amount):
    return (
        dates.fmt(date),
        payer,
        money.to_won(amount),
    )


def export_csv(store, path, start=None, end=None, category=None):
    """CSV로 내보낸다. UTF-8 BOM을 사용한다. (건수, 합계)"""
    expenses = _selected_expenses(store, start, end, category)
    total = _record_total(expenses)

    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for expense in expenses:
            writer.writerow(_expense_to_csv_row(expense))

    return len(expenses), total


def export_json(store, path, start=None, end=None, category=None):
    """JSON으로 내보낸다. (건수, 합계)"""
    expenses = _selected_expenses(store, start, end, category)
    total = _record_total(expenses)

    data = [copy.deepcopy(e) for e in expenses]

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return len(expenses), total


def file_total(path):
    """내보낸 파일의 금액 합계와 건수를 반환한다."""
    rows = _read_export(path)

    total = 0

    for row in rows:
        if not isinstance(row, dict) or "amount" not in row:
            raise ValueError("파일의 지출 금액 항목이 잘못되었습니다")

        total += money.to_won(row["amount"])

    return len(rows), total


def verify_export(store, path, start=None, end=None, category=None):
    """파일 합계와 원래 기록 합계를 비교한다."""
    _, file_sum = file_total(path)

    expenses = _selected_expenses(store, start, end, category)
    record_sum = _record_total(expenses)

    return file_sum == record_sum, file_sum, record_sum


def roundtrip_check(store, path, start=None, end=None, category=None):
    """내보낸 자료를 다시 읽어 원본과 비교한다.

    다른 지출 번호 목록을 반환한다.
    """
    original = _selected_expenses(store, start, end, category)
    exported = _read_export(path)

    original_by_id = {
        expense["id"]: expense
        for expense in original
    }

    exported_by_id = {}

    for row in exported:
        try:
            eid = int(row["id"])
        except (KeyError, TypeError, ValueError):
            continue

        exported_by_id[eid] = row

    all_ids = set(original_by_id) | set(exported_by_id)
    different = []

    compare_fields = (
        "date",
        "payer",
        "amount",
        "members",
        "memo",
        "category",
        "weights",
    )

    for eid in sorted(all_ids):
        before = original_by_id.get(eid)
        after = exported_by_id.get(eid)

        if before is None or after is None:
            different.append(eid)
            continue

        same = True

        for field in compare_fields:
            left = before.get(field)
            right = after.get(field)

            if field == "date":
                left = dates.fmt(left)
                right = dates.fmt(right)

            elif field == "amount":
                left = money.to_won(left)
                right = money.to_won(right)

            elif field == "members":
                left = list(left or [])
                right = (
                    right.split(";")
                    if isinstance(right, str)
                    else list(right or [])
                )

            elif field == "category":
                left = left or None
                right = right or None

            elif field == "weights":
                if isinstance(right, str):
                    try:
                        right = json.loads(right)
                    except ValueError:
                        right = None

            if left != right:
                same = False
                break

        if not same:
            different.append(eid)

    return different


def import_csv(store, path, mapping=None, encoding=None, preview=False):
    """CSV 지출을 가져온다.

    반환값:
    {
        "encoding": 인코딩,
        "added": 추가한 번호 또는 미리보기 줄 번호,
        "duplicates": 중복 줄 번호,
        "errors": [(줄 번호, 오류)]
    }
    """
    detected, rows = read_csv_rows(
        path,
        mapping=mapping,
        encoding=encoding,
    )

    result = {
        "encoding": detected,
        "added": [],
        "duplicates": [],
        "errors": [],
    }

    seen = set()

    for line_number, row in rows:
        try:
            expense = _row_to_expense(row)

            # 공통 유효성 검사
            date, amount = ledger.validate(
                store,
                expense["date"],
                expense["payer"],
                expense["amount"],
                expense["members"],
                expense["weights"],
            )

            signature = _expense_signature(
                date,
                expense["payer"],
                amount,
            )

            # 파일 내부 중복 확인
            if signature in seen:
                result["duplicates"].append(line_number)
                continue

            # 기존 자료와 중복 확인
            duplicate_ids = ledger.duplicates(
                store,
                date,
                expense["payer"],
                amount,
            )

            if duplicate_ids:
                result["duplicates"].append(line_number)
                seen.add(signature)
                continue

            seen.add(signature)

            if preview:
                result["added"].append(line_number)
                continue

            # 실제 지출 저장
            inserted = ledger.insert(
                store,
                date,
                expense["payer"],
                amount,
                expense["members"],
                memo=expense["memo"],
                weights=expense["weights"],
                category=expense["category"],
            )

            result["added"].append(inserted["id"])

        except Exception as exc:
            result["errors"].append((line_number, str(exc)))

    return result


def backup_all(store, path):
    """전체 자료를 JSON 백업 파일로 저장한다."""
    data = copy.deepcopy(store.data)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return path


def restore_all(store, path):
    """백업 파일을 검사한 뒤 자료를 복원한다."""
    with open(path, "r", encoding="utf-8") as file:
        restored = json.load(file)

    if not isinstance(restored, dict):
        raise ValueError("백업 파일 형식이 잘못되었습니다")

    restored = copy.deepcopy(restored)
    store._check_shape(restored)

    # 원본 자료를 검사 중에 변경하지 않고 마지막에 교체한다.
    store.data = restored

    return True


def merge(store, other_path):
    """다른 모임의 백업 자료를 합친다. 지출 번호는 새로 발급한다."""
    with open(other_path, "r", encoding="utf-8") as file:
        other = json.load(file)

    if not isinstance(other, dict):
        raise ValueError("병합할 백업 파일 형식이 잘못되었습니다")

    other = copy.deepcopy(other)
    store._check_shape(other)

    # 기존 자료를 복사해 작업한다.
    merged = copy.deepcopy(store.data)

    # 회원은 이름을 기준으로 병합한다.
    members_by_name = {
        member["name"]: member
        for member in merged.get("members", [])
    }

    for incoming in other.get("members", []):
        name = incoming.get("name")

        if not name:
            raise ValueError("회원 자료에 이름이 없습니다")

        if name not in members_by_name:
            new_member = copy.deepcopy(incoming)
            merged["members"].append(new_member)
            members_by_name[name] = new_member
            continue

        # 같은 회원이면 가입일은 빠른 날짜, 탈퇴일은 늦은 날짜를 사용한다.
        current = members_by_name[name]

        if incoming.get("joined"):
            if (
                not current.get("joined")
                or dates.parse(incoming["joined"])
                < dates.parse(current["joined"])
            ):
                current["joined"] = incoming["joined"]

        current_left = current.get("left")
        incoming_left = incoming.get("left")

        # 어느 한쪽이라도 현재 회원이면 탈퇴일은 없는 것으로 처리한다.
        if current_left is None or incoming_left is None:
            current["left"] = None
        elif dates.parse(incoming_left) > dates.parse(current_left):
            current["left"] = incoming_left

    # 새 지출 번호가 기존 번호와 겹치지 않도록 보정한다.
    existing_ids = [
        int(e["id"])
        for e in merged.get("expenses", [])
        if "id" in e
    ]

    next_id = max(
        int(merged.get("next_id", 1)),
        max(existing_ids, default=0) + 1,
    )

    # 지출은 삭제 표시를 포함해 모두 병합한다.
    new_expenses = []

    for incoming in other.get("expenses", []):
        if not isinstance(incoming, dict):
            raise ValueError("지출 자료 형식이 잘못되었습니다")

        expense = copy.deepcopy(incoming)
        expense["id"] = next_id
        next_id += 1
        new_expenses.append(expense)

    merged.setdefault("expenses", []).extend(new_expenses)
    merged["next_id"] = next_id

    # 모든 작업이 성공한 뒤 원본 자료에 반영한다.
    store.data = merged

    return len(new_expenses)
