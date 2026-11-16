
"""기능 6. 가져오기·내보내기.

담당: 기능 6(류강현)
"""

import csv
import copy
import json

from ..common import dates, ledger, money
from ..common.csvio import detect_encoding, read_csv_rows
from ..common.queries import active_members, expenses_in


# CSV 내보내기에서 사용할 열 이름과 순서
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


def _selected_expenses(store, start=None, end=None, category=None):
    """기간·분류 조건에 맞는 삭제되지 않은 지출을 가져온다."""
    if start is not None and end is not None:
        expenses = expenses_in(store, start, end)
    else:
        expenses = store.data.get("expenses", [])

    result = []

    for expense in expenses:
        if expense.get("deleted", False):
            continue

        if start is not None and dates.parse(expense["date"]) < dates.parse(start):
            continue

        if end is not None and dates.parse(expense["date"]) > dates.parse(end):
            continue

        expense_category = expense.get("category") or "미분류"

        if category is not None and expense_category != category:
            continue

        result.append(expense)

    return sorted(result, key=lambda e: e["id"])


def _expense_to_csv_row(expense):
    """지출 한 건을 CSV 행으로 바꾼다."""
    return {
        "id": expense["id"],
        "date": dates.fmt(expense["date"]),
        "payer": expense["payer"],
        "amount": money.to_won(expense["amount"]),
        "members": ";".join(expense.get("members", [])),
        "memo": expense.get("memo", ""),
        "category": expense.get("category") or "",
        "weights": json.dumps(
            expense.get("weights"),
            ensure_ascii=False,
        ),
    }


def _row_to_expense(row):
    """CSV 행을 지출 자료 형식으로 바꾼다."""
    members_text = row.get("members", "")
    members = [
        name.strip()
        for name in members_text.split(";")
        if name.strip()
    ]

    weights_text = row.get("weights", "").strip()
    weights = json.loads(weights_text) if weights_text else None

    return {
        "date": dates.fmt(row["date"]),
        "payer": row["payer"].strip(),
        "amount": money.to_won(row["amount"]),
        "members": members,
        "memo": row.get("memo", ""),
        "category": row.get("category") or None,
        "weights": weights,
    }


def export_csv(store, path, start=None, end=None, category=None):
    """CSV 로 내보낸다(엑셀에서 한글이 깨지지 않게 UTF-8 BOM)."""
    expenses = _selected_expenses(store, start, end, category)
    total = sum(money.to_won(e["amount"]) for e in expenses)

    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for expense in expenses:
            writer.writerow(_expense_to_csv_row(expense))

    return len(expenses), total


def export_json(store, path, start=None, end=None, category=None):
    """지출 자료를 JSON 파일로 내보낸다."""
    expenses = _selected_expenses(store, start, end, category)
    total = sum(money.to_won(e["amount"]) for e in expenses)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            [copy.deepcopy(e) for e in expenses],
            file,
            ensure_ascii=False,
            indent=2,
        )

    return len(expenses), total


def file_total(path):
    """내보낸 파일의 금액 합계와 건수를 구한다."""
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as file:
            expenses = json.load(file)

        if not isinstance(expenses, list):
            raise ValueError("JSON 파일 형식이 올바르지 않습니다")

        total = sum(
            money.to_won(e["amount"])
            for e in expenses
        )
        return len(expenses), total

    encoding = detect_encoding(path)

    with open(path, encoding=encoding, newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    total = sum(
        money.to_won(row["amount"])
        for row in rows
    )

    return len(rows), total


def verify_export(store, path, start=None, end=None, category=None):
    """내보낸 파일 합계와 원래 기록 합계를 비교한다."""
    _, file_sum = file_total(path)

    expenses = _selected_expenses(store, start, end, category)
    record_sum = sum(
        money.to_won(e["amount"])
        for e in expenses
    )

    return file_sum == record_sum, file_sum, record_sum


def roundtrip_check(store, path, start=None, end=None, category=None):
    """내보낸 파일을 다시 읽어 원래 기록과 비교한다."""
    original = _selected_expenses(store, start, end, category)
    original_by_id = {
        e["id"]: e for e in original
    }

    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as file:
            imported = json.load(file)
    else:
        encoding = detect_encoding(path)
        _, rows = read_csv_rows(path, encoding=encoding)
        imported = []

        for _, row in rows:
            imported.append(_row_to_expense(row))

    different = []

    if path.lower().endswith(".json"):
        imported_by_id = {
            e["id"]: e for e in imported
        }

        all_ids = set(original_by_id) | set(imported_by_id)

        for eid in sorted(all_ids):
            if original_by_id.get(eid) != imported_by_id.get(eid):
                different.append(eid)

    else:
        # CSV의 각 행은 원본 지출과 순서대로 비교한다.
        if len(original) != len(imported):
            different.extend(
                e["id"] for e in original
            )

        for index, expense in enumerate(original):
            if index >= len(imported):
                break

            row = imported[index]
            try:
                restored = _row_to_expense(row)
            except (KeyError, ValueError, TypeError, json.JSONDecodeError):
                different.append(expense["id"])
                continue

            keys = (
                "date",
                "payer",
                "amount",
                "members",
                "memo",
                "category",
                "weights",
            )

            if any(
                expense.get(key) != restored.get(key)
                for key in keys
            ):
                different.append(expense["id"])

    return sorted(set(different))


def import_csv(store, path, mapping=None, encoding=None, preview=False):
    """CSV 지출을 가져온다."""
    used_encoding, rows = read_csv_rows(
        path,
        mapping=mapping,
        encoding=encoding,
    )

    result = {
        "encoding": used_encoding,
        "added": [],
        "duplicates": [],
        "errors": [],
    }

    for line_number, row in rows:
        try:
            expense = _row_to_expense(row)

            # 지출 입력 규칙을 먼저 검사한다.
            date, amount = ledger.validate(
                store,
                expense["date"],
                expense["payer"],
                expense["amount"],
                expense["members"],
                expense["weights"],
            )

            # 같은 날짜·낸 사람·금액의 지출이 있는지 확인한다.
            duplicate_ids = ledger.duplicates(
                store,
                date,
                expense["payer"],
                amount,
            )

            if duplicate_ids:
                result["duplicates"].append(line_number)
                continue

            if preview:
                result["added"].append(line_number)
                continue

            # 실제 지출 저장은 공통 함수에 맡긴다.
            saved = ledger.insert(
                store,
                date,
                expense["payer"],
                amount,
                expense["members"],
                memo=expense["memo"],
                weights=expense["weights"],
                category=expense["category"],
            )

            result["added"].append(saved["id"])

        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            result["errors"].append((line_number, str(error)))

    return result


def backup_all(store, path):
    """모임의 전체 자료를 JSON 백업 파일로 저장한다."""
    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            store.data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return path


def restore_all(store, path):
    """JSON 백업 파일에서 전체 자료를 복원한다."""
    with open(path, encoding="utf-8") as file:
        restored = json.load(file)

    # 정상적인 모임 자료 구조인지 검사한다.
    from ..common.store import Store

    Store._check_shape(restored)

    store.data = copy.deepcopy(restored)
    return store


def merge(store, other_path):
    """다른 모임 자료의 회원·지출을 현재 모임에 합친다."""
    with open(other_path, encoding="utf-8") as file:
        other = json.load(file)

    from ..common.store import Store

    Store._check_shape(other)

    # 기존 회원 이름을 기준으로 중복 회원을 방지한다.
    member_names = {
        member["name"]
        for member in store.data.get("members", [])
    }

    for member in other.get("members", []):
        if member["name"] not in member_names:
            store.data["members"].append(copy.deepcopy(member))
            member_names.add(member["name"])

    # 지출 번호는 현재 모임에서 새로 발급한다.
    added_count = 0

    for expense in other.get("expenses", []):
        new_expense = copy.deepcopy(expense)
        new_expense["id"] = store.new_id()

        store.data["expenses"].append(new_expense)
        added_count += 1

    return added_count
 end=None, category=None):
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
