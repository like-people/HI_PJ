"""기능 6. 가져오기·내보내기.

이 기능을 구현하려면 아래 공통 함수를 이 기능 담당자가 채운다(공통 모듈 병합 요청으로).
  - common/ledger.py duplicates — 같은 날·같은 사람·같은 금액 지출 찾기(공용: 기능 1)
  - common/dates.py month_key — 날짜의 달 이름(공용: 기능 3)
  - common/queries.py period_total — 기간 합계(공용: 기능 3·5)
  - common/csvio.py detect_encoding, read_csv_rows — 인코딩 판별과 CSV 읽기(공용: 기능 5의 은행 거래내역 가져오기)

아래 함수의 이름과 인자는 바꾸지 않는다(인수 테스트와 채점이 이 이름으로 실행된다).
필요하면 함수를 더 만들어도 된다. 다른 기능 파일은 불러 쓰지 않는다.
"""

import os
import tempfile
import csv
import copy
import json
from ..common import dates, ledger, money
from ..common.csvio import detect_encoding, read_csv_rows  # noqa: F401
from ..common.queries import active_members, expenses_in, category_of


def _filtered_expenses(store, start=None, end=None, category=None):
    """기간과 분류 조건에 맞는 지출 목록을 반환한다."""
    start_date = start or "0001-01-01"
    end_date = end or "9999-12-31"

    expenses = expenses_in(store, start_date, end_date)

    if category is not None:
        expenses = [
            e for e in expenses
            if category_of(e) == category
        ]

    return expenses


def export_csv(store, path, start=None, end=None, category=None):
    """CSV 로 내보낸다(엑셀에서 한글이 깨지지 않게 UTF-8 BOM). 돌려주는 값: (건수, 합계)"""
    expenses = _filtered_expenses(store, start, end, category)

    headers = [
        "id", "date", "payer", "amount",
        "members", "weights", "category", "memo",
    ]

    total = 0

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for e in expenses:
            members = e["members"]
            weights = e.get("weights")

            members_text = ";".join(members)
            weights_text = (
                ";".join(f"{name}:{weights[name]}" for name in members)
                if weights else ""
            )

            writer.writerow([
                e["id"],
                e["date"],
                e["payer"],
                e["amount"],
                members_text,
                weights_text,
                e.get("category") or "",
                e.get("memo") or "",
            ])

            total += e["amount"]

    return len(expenses), total


def export_json(store, path, start=None, end=None, category=None):
    """JSON 으로 내보낸다(규격 6-2 5번). 돌려주는 값: (건수, 합계)"""
    # 최상위는 객체이고 지출은 "expenses" 배열로 내보낸다.
    # 분류가 없으면 null, 균등 분배면 weights 는 null. 삭제한 지출은 필터에서 제외한다.
    expenses = _filtered_expenses(store, start, end, category)
    rows = [
        {
            "id": e["id"],
            "date": e["date"],
            "payer": e["payer"],
            "amount": e["amount"],
            "members": list(e["members"]),
            "weights": dict(e["weights"]) if e.get("weights") else None,
            "category": e.get("category") or None,
            "memo": e.get("memo") or "",
        }
        for e in expenses
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"expenses": rows}, f, ensure_ascii=False, indent=2)
    return len(rows), sum(row["amount"] for row in rows)


def file_total(path):
    """내보낸 파일의 금액 합계와 건수를 반환한다: (건수, 합계)."""
    if str(path).lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            if "expenses" not in data:
                raise ValueError("JSON 파일에 expenses 필드가 없습니다")
            rows = data["expenses"]
            if not isinstance(rows, list):
                raise ValueError("JSON 파일의 expenses 형식이 올바르지 않습니다")
        elif isinstance(data, list):
            rows = data
        else:
            raise ValueError("JSON 파일 형식이 올바르지 않습니다")

        if any(not isinstance(row, dict) for row in rows):
            raise ValueError("JSON 지출 항목 형식이 올바르지 않습니다")

        rows = [
            row for row in rows
            if not row.get("deleted", False)
        ]

        total = 0
        for row in rows:
            if "amount" not in row:
                raise ValueError("JSON 거래에 amount 필드가 없습니다")
            total += money.to_won(row["amount"])

        return len(rows), total

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None or "amount" not in reader.fieldnames:
            raise ValueError("CSV 파일에 amount 열이 없습니다")

        count = 0
        total = 0

        for row in reader:
            if not row:
                continue

            amount = row.get("amount", "").strip()

            count += 1
            total += money.to_won(amount)

    return count, total


def verify_export(store, path, start=None, end=None, category=None):
    """내보낸 파일 합계가 원래 기록 합계와 같은가. 돌려주는 값: (같은가, 파일 합계, 기록 합계)"""
    expenses = _filtered_expenses(store, start, end, category)

    record_total = sum(e["amount"] for e in expenses)

    _, file_sum = file_total(path)

    matched = record_total == file_sum

    return matched, file_sum, record_total


def roundtrip_check(store, path, start=None, end=None, category=None):
    """CSV 파일을 읽어 원래 기록과 비교한다. 다른 번호 목록을 반환한다."""
    expenses = _filtered_expenses(store, start, end, category)

    # 원본 지출을 CSV 문자열 형식으로 변환
    expected = {}
    for e in expenses:
        eid = str(e["id"])
        members = e["members"]
        weights = e.get("weights")

        expected[eid] = [
            eid,
            e["date"],
            e["payer"],
            str(e["amount"]),
            ";".join(members),
            (
                ";".join(f"{name}:{weights[name]}" for name in members)
                if weights else ""
            ),
            e.get("category") or "",
            e.get("memo") or "",
        ]

    # 지정된 파일은 읽기만 한다. 절대 다시 내보내지 않는다.
    actual = {}
    duplicate_ids = set()

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        required_headers = [
            "id", "date", "payer", "amount",
            "members", "weights", "category", "memo",
        ]
        if reader.fieldnames is None or any(
            header not in reader.fieldnames for header in required_headers
        ):
            raise ValueError("CSV 파일의 필수 열이 없습니다")

        for row in reader:
            eid = row["id"]

            if eid in actual:
                duplicate_ids.add(eid)
                continue

            actual[eid] = [
                row["id"],
                row["date"],
                row["payer"],
                row["amount"],
                row["members"],
                row["weights"],
                row["category"],
                row["memo"],
            ]

    # 값이 다르거나 누락·추가·중복된 ID
    different = set(duplicate_ids)
    all_ids = set(expected) | set(actual)

    for eid in all_ids:
        if expected.get(eid) != actual.get(eid):
            different.add(eid)

    # 지출 ID는 정수만 허용한다. 비숫자 ID는 ValueError로 명확히 처리.
    try:
        result_ids = [int(eid) for eid in different]
    except (TypeError, ValueError) as exc:
        raise ValueError("CSV 지출 ID는 정수여야 합니다") from exc

    return sorted(result_ids)


def import_csv(store, path, mapping=None, encoding=None, preview=False):
    """CSV 지출을 가져온다. 돌려주는 값: {"encoding", "added": [번호], "duplicates": [줄 번호], "errors": [(줄 번호, 오류)]}
    preview=True 면 실제로 넣지 않고 검사만 한다. 이때 added 에는 들어갈 줄 번호가 담긴다."""
    raise NotImplementedError("이 함수를 구현한다")


def backup_all(store, path):
    """현재 모임 자료 전체를 JSON 백업 파일로 저장한다."""

    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".moim-backup-",
            suffix=".tmp",
            delete=False,
        ) as f:
            temp_path = f.name
            json.dump(store.data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, path)
        temp_path = None

    finally:
        if temp_path is not None and os.path.exists(temp_path):
            os.remove(temp_path)


def restore_all(store, path):
    """JSON 백업 파일을 읽어 현재 모임 자료 전체를 메모리에 복원한다.
    실제 자료 파일 저장은 호출 측에서 복원 성공을 확인한 뒤
    Store.save()를 호출해 처리한다."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("백업 파일 형식이 올바르지 않습니다")

    store._check_shape(data)
    store.data = copy.deepcopy(data)

    return store


def merge(store, other_path, report=None):
    """다른 모임 자료의 회원·지출을 합친다. 지출 번호는 새로 매긴다."""
    with open(other_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("병합 파일 형식이 올바르지 않습니다")
    if not isinstance(data.get("members"), list):
        raise ValueError("병합 파일의 members 형식이 올바르지 않습니다")
    if not isinstance(data.get("expenses"), list):
        raise ValueError("병합 파일의 expenses 형식이 올바르지 않습니다")

    added, skipped, duplicates = 0, [], []
    existing_names = {m["name"] for m in store.data["members"] if m.get("name")}

    for member in data["members"]:
        name = member.get("name") if isinstance(member, dict) else None
        try:
            if not name or not member.get("joined"):
                raise ValueError("회원의 필수 항목이 없습니다: name, joined")
            joined = dates.parse(member["joined"])
            left = dates.parse(member["left"]) if member.get("left") else None
            if left and left < joined:
                raise ValueError("탈퇴일이 가입일보다 빠릅니다")
        except (ValueError, TypeError) as exc:
            skipped.append({"id": name, "reason": str(exc)})
            continue
        if name not in existing_names:
            store.data["members"].append(copy.deepcopy(member))
            existing_names.add(name)

    for expense in data["expenses"]:
        if not isinstance(expense, dict) or expense.get("deleted", False):
            continue
        original_id = expense.get("id")
        missing = [key for key in ("date", "payer", "amount", "members") if key not in expense]
        if missing:
            skipped.append({
                "id": original_id,
                "reason": f"필수 항목이 없습니다: {', '.join(missing)}",
            })
            continue
        try:
            duplicate_ids = ledger.duplicates(store, expense["date"], expense["payer"], expense["amount"])
            ledger.insert(
                store, date=expense["date"], payer=expense["payer"], amount=expense["amount"],
                members=expense["members"], memo=expense.get("memo", ""),
                weights=expense.get("weights"), category=expense.get("category"),
                recurring_id=None, action="add",
            )
            added += 1
            if duplicate_ids:
                duplicates.append({"id": original_id, "matches": duplicate_ids})
        except (ValueError, KeyError, TypeError) as exc:
            skipped.append({"id": original_id, "reason": str(exc)})

    if report is not None:
        report["skipped"] = skipped
        report["duplicates"] = duplicates
    return added
