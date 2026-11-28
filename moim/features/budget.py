"""기능 5. 예산·회비. 담당: 이정배.

이 기능을 구현하려면 아래 공통 함수를 이 기능 담당자가 채운다(공통 모듈 병합 요청으로).
 - common/queries.py is_member_active - 그날 회원인가(공용: 기능 1의 지출 검사)
 - common/queries.py active_members - 그날 회원 목록
 - common/dates.py months_between - 두 달 사이의 달 목록(공용: 기능 3)
 - 은행 거래내역 가져오는 기능 6이 채우는 common/csvio.py 의 read_csv_rows 를 쓴다

이 기능에 필요한 자료 항목은 common/store.py 의 EMPTY 에 이 기능 담당자가 추가한다.
 - 회비 입금(payments 목록)

아래 함수의 이름과 인자는 바꾸지 않는다(인수 테스트와 채점이 이 이름으로 실행된다).
필요하면 함수를 더 만들어도 된다. 다른 기능 파일은 불러 쓰지 않는다.

"""

from csv import Error as CsvError
from decimal import Decimal, DecimalException

from ..common import dates, ledger, money
from ..common.csvio import read_csv_rows
from ..common.queries import active_members, category_totals, period_total


def month_status(store, cfg, month, today=None):
    """이번 달 예산 상태. today 를 주면 그날까지의 지출만 센다."""
    year, mon = dates.parse_month(month)
    start, end = dates.month_range(year, mon)

    if today is None:
        spent = period_total(store, start, end)
    else:
        today_date = dates.parse(today)
        if today_date < start:
            spent = 0
        else:
            spent = period_total(store, start, min(end, today_date))

    monthly = cfg.get("budget", {}).get("monthly")
    if monthly is None:
        return {
            "budget": None,
            "spent": spent,
            "remaining": None,
            "over": False,
            "warn": False,
        }

    if isinstance(monthly, bool) or not isinstance(monthly, int) or monthly < 0:
        raise ValueError("월 예산은 0 이상의 정수여야 합니다")

    warn_ratio = cfg.get("warn_ratio", 0.8)
    if (
        isinstance(warn_ratio, bool)
        or not isinstance(warn_ratio, (int, float))
        or not (0 <= warn_ratio <= 1)
    ):
        raise ValueError("경고 비율(warn_ratio)은 0 이상 1 이하의 숫자여야 합니다")

    remaining = monthly - spent
    over = spent > monthly
    if monthly == 0:
        warn = spent > 0
    else:
        warn = Decimal(spent) > Decimal(monthly) * Decimal(str(warn_ratio))

    return {
        "budget": monthly,
        "spent": spent,
        "remaining": remaining,
        "over": over,
        "warn": warn,
    }


def category_status(store, cfg, month):
    """분류별 예산 상태. {분류: {"budget", "spent", "remaining", "over", "warn"}}"""
    year, mon = dates.parse_month(month)
    start, end = dates.month_range(year, mon)

    by_category = cfg.get("budget", {}).get("by_category")
    if not by_category:
        return {}

    ratio = None
    if any(limit is not None for limit in by_category.values()):
        warn_ratio = cfg.get("warn_ratio", 0.8)
        if (
            isinstance(warn_ratio, bool)
            or not isinstance(warn_ratio, (int, float))
            or not (0 <= warn_ratio <= 1)
        ):
            raise ValueError("경고 비율(warn_ratio)은 0 이상 1 이하의 숫자여야 합니다")
        ratio = Decimal(str(warn_ratio))

    totals = category_totals(store, start, end)
    result = {}

    for category, limit in by_category.items():
        spent = totals.get(category, {}).get("amount", 0)
        if limit is None:
            result[category] = {
                "budget": None,
                "spent": spent,
                "remaining": None,
                "over": False,
                "warn": False,
            }
            continue

        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError(f"분류 예산은 0 이상의 정수여야 합니다: {category}")

        remaining = limit - spent
        over = spent > limit
        warn = spent > 0 if limit == 0 else Decimal(spent) > Decimal(limit) * ratio
        result[category] = {
            "budget": limit,
            "spent": spent,
            "remaining": remaining,
            "over": over,
            "warn": warn,
        }

    return result


def forecast(store, month, today):
    """지금 속도로 쓰면 월말 합계가 얼마가 되는지. (오늘까지 지출 / 지난 일수) x 그달 일수."""
    year, mon = dates.parse_month(month)
    start, end = dates.month_range(year, mon)
    today_date = dates.parse(today)

    if today_date < start:
        return 0
    if today_date >= end:
        return period_total(store, start, end)

    elapsed_days = (today_date - start).days + 1
    days_in_month = (end - start).days + 1
    spent = period_total(store, start, today_date)
    projected = (Decimal(spent) * Decimal(days_in_month)) / Decimal(elapsed_days)
    return money.to_won(projected)


def record_payment(store, date, member, amount, memo=""):
    """회비 입금을 메모리 자료에 추가하고 추가한 기록을 반환한다."""
    payment_date = dates.fmt(date)
    payment_amount = money.to_won(amount)

    if payment_amount <= 0:
        raise ValueError("회비 입금액은 1원 이상이어야 합니다")
    if store.member(member) is None:
        raise ValueError(f"명부에 없는 회원입니다: {member}")

    payment = {
        "date": payment_date,
        "member": member,
        "amount": payment_amount,
        "memo": memo,
        "source": "manual",
    }
    store.data["payments"].append(payment)
    return payment


def treasury_balance(store, until=None):
    """모임 통장 잔고 = 회비 입금 합계 - 지출 합계(until 날짜까지)."""
    until_date = dates.parse(until) if until is not None else None

    payment_total = sum(
        payment["amount"]
        for payment in store.data.get("payments", [])
        if until_date is None or dates.parse(payment["date"]) <= until_date
    )

    expense_dates = [
        dates.parse(expense["date"])
        for expense in store.data.get("expenses", [])
        if not expense.get("deleted")
    ]
    if not expense_dates:
        expense_total = 0
    else:
        earliest = min(expense_dates)
        latest = max(expense_dates) if until_date is None else until_date
        if latest < earliest:
            expense_total = 0
        else:
            expense_total = period_total(store, earliest, latest)

    return payment_total - expense_total


def unpaid(store, cfg, month):
    """그달 회비 미납자. 그달 1일 또는 말일에 회원인 사람이 대상.
    [(이름, 낸 회비, 모자란 금액)]
    """
    year, mon = dates.parse_month(month)
    start, end = dates.month_range(year, mon)

    monthly = cfg["dues"]["monthly"]
    if monthly is None:
        return []

    if isinstance(monthly, bool) or not isinstance(monthly, int) or monthly < 0:
        raise ValueError("월 회비는 0 이상의 정수여야 합니다")

    # 월초 또는 월말에 회원인 사람
    eligible = set(active_members(store, start))
    eligible.update(active_members(store, end))

    # 해당 월의 입금 합계
    paid = {}
    for payment in store.data.get("payments", []):
        if dates.in_period(payment["date"], start, end):
            name = payment["member"]
            paid[name] = paid.get(name, 0) + payment["amount"]

    # 명부 순서대로 미납자 조회
    result = []
    for member in store.data["members"]:
        name = member["name"]

        if name not in eligible:
            continue

        amount = paid.get(name, 0)
        shortage = max(0, monthly - amount)

        if shortage > 0:
            result.append((name, amount, shortage))

    return result


# 담당: 기능 5(이정배)
def dues_deduction(store, cfg, month):
    """회비를 덜 낸 사람에게 정산에서 차감할 금액. {이름: 모자란 회비}"""
    return {
        name: shortage
        for name, _paid, shortage in unpaid(store, cfg, month)
    }


def budget_table(store, cfg, month):
    """예산 대비 실제 표 자료. [(분류, 예산, 실제, 차이)] 마지막 줄은 전체."""
    year, mon = dates.parse_month(month)
    start, end = dates.month_range(year, mon)

    budget_cfg = cfg.get("budget", {})
    by_category = budget_cfg.get("by_category") or {}
    monthly = budget_cfg.get("monthly")

    if monthly is not None and (
        isinstance(monthly, bool) or not isinstance(monthly, int) or monthly < 0
    ):
        raise ValueError("월 예산은 0 이상의 정수여야 합니다")

    totals = category_totals(store, start, end)
    rows = []

    for category, limit in by_category.items():
        spent = totals.get(category, {}).get("amount", 0)
        if limit is None:
            rows.append((category, None, spent, None))
            continue
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError(f"분류 예산은 0 이상의 정수여야 합니다: {category}")
        rows.append((category, limit, spent, limit - spent))

    for category, info in totals.items():
        if category in by_category:
            continue
        spent = info["amount"]
        rows.append((category, 0, spent, -spent))

    total_spent = period_total(store, start, end)
    if monthly is None:
        rows.append(("전체", None, total_spent, None))
    else:
        rows.append(("전체", monthly, total_spent, monthly - total_spent))

    return rows


def suggest_budget(store, month):
    """다음 달 예산 제안: 그달을 포함한 최근 3개월 지출 평균(천 원 단위 올림)."""
    year, mon = dates.parse_month(month)
    total_index = year * 12 + (mon - 1)
    start_index = total_index - 2
    start_ym = (start_index // 12, start_index % 12 + 1)
    end_ym = (year, mon)
    first_start, _ = dates.month_range(*start_ym)
    _, last_end = dates.month_range(*end_ym)
    total = period_total(store, first_start, last_end)

    return ((total + 2999) // 3000) * 1000


BANK_COLUMNS = ["거래일자", "거래시각", "적요", "출금액", "입금액", "잔액"]


def _bank_amount(value):
    if not value:
        return 0
    try:
        return money.to_won(value)
    except (DecimalException, OverflowError):
        raise ValueError(f"금액 형식이 잘못되었습니다: {value}") from None


def import_bank(store, path, treasurer):
    """가상 은행(Tarnwick 제휴 은행) 거래내역을 가져온다(docs/은행거래내역형식.md).
    출금 -> 총무가 낸 지출(참여자: 그날의 회원 전원), 입금 -> 적요의 이름으로 회비 입금.
    이미 들어간 거래(같은 날·같은 금액·같은 적요의 출금, 같은 날·같은 사람·같은 금액의 입금)와
    파일 안에서 거래일자·거래시각·적요·금액·잔액이 모두 같은 줄은 중복으로 보고 건너뛴다.
    돌려주는 값: {"expenses": [번호], "payments": 건수, "duplicates": [줄 번호], "errors": [(줄 번호, 오류)]}"""
    try:
        _, rows = read_csv_rows(path)
    except CsvError as exc:
        raise ValueError(f"은행 CSV를 읽을 수 없습니다: {exc}") from exc

    result = {"expenses": [], "payments": 0, "duplicates": [], "errors": []}
    # 가져오기 전 기록과 비교한다. 같은 파일에서는 여섯 열이 모두 같은 행만 중복이다.
    expenses = {
        (expense["date"], expense["amount"], expense.get("memo", ""))
        for expense in store.data["expenses"]
        if not expense.get("deleted")
    }
    payments = {
        (payment["date"], payment["member"], payment["amount"])
        for payment in store.data["payments"]
    }
    seen = set()
    for line, row in rows:
        try:
            missing = [column for column in BANK_COLUMNS if column not in row]
            if missing:
                raise ValueError(f"은행 CSV에 필요한 열이 없습니다: {', '.join(missing)}")
            fields = tuple(row[column] for column in BANK_COLUMNS)
            if fields in seen:
                result["duplicates"].append(line)
                continue

            date = dates.fmt(row["거래일자"].replace(".", "-"))
            memo = row["적요"]
            withdrawal = _bank_amount(row["출금액"])
            deposit = _bank_amount(row["입금액"])
            if withdrawal < 0 or deposit < 0:
                raise ValueError("출금액과 입금액은 음수일 수 없습니다")
            if bool(withdrawal) == bool(deposit):
                raise ValueError("출금액과 입금액 중 하나만 1원 이상이어야 합니다")

            if withdrawal:
                if (date, withdrawal, memo) in expenses:
                    result["duplicates"].append(line)
                    continue
                if not treasurer:
                    raise ValueError("총무를 설정하거나 --treasurer로 지정해 주세요")
                expense = ledger.insert(
                    store, date, treasurer, withdrawal, active_members(store, date), memo=memo
                )
                result["expenses"].append(expense["id"])
            else:
                if (date, memo, deposit) in payments:
                    result["duplicates"].append(line)
                    continue
                payment = record_payment(store, date, memo, deposit)
                payment["source"] = "bank"
                result["payments"] += 1
            seen.add(fields)
        except ValueError as exc:
            result["errors"].append((line, str(exc)))

    return result