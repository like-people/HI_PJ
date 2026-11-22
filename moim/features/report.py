"""기능 3. 월별·기간 보고서.

이 기능을 구현하려면 아래 공통 함수를 이 기능 담당자가 채운다(공통 모듈 병합 요청으로).
  - common/queries.py expenses_in — 기간 안의 지출 목록(공용: 전원)
  - common/queries.py person_paid — 사람별 낸 돈(공용: 기능 4)
  - common/textfmt.py table, bar_chart — 글자 표와 막대그래프(공용: 기능 1·4·5의 명령)

아래 함수의 이름과 인자는 바꾸지 않는다(인수 테스트와 채점이 이 이름으로 실행된다).
필요하면 함수를 더 만들어도 된다. 다른 기능 파일은 불러 쓰지 않는다.
"""

import datetime as dt
import os
from ..common import dates, money
from ..common.textfmt import bar_chart, pad, table, width  # noqa: F401  (보고서 기능의 표 출력은 공통 함수로 제공)
from ..common.queries import category_totals, expenses_in, period_total, person_paid

WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


# 담당: 기능 3(류훈태)
def monthly_totals(store, start_month, end_month):
    """{'YYYY-MM': 합계}"""
    totals = {}
    for year, month in dates.months_between(dates.parse_month(start_month), dates.parse_month(end_month)):
        first, last = dates.month_range(year, month)
        totals[dates.month_key(first)] = period_total(store, first, last)
    return totals


# 담당: 기능 3(류훈태)
def period_summary(store, start, end):
    """기간 보고: {"total": 합계, "by_category": {분류: 금액}, "by_person": {이름: 낸 돈}}"""
    return {
        "total": period_total(store, start, end),
        "by_category": {name: v["amount"] for name, v in category_totals(store, start, end).items()},
        "by_person": person_paid(store, start, end),
    }

def _month_sum(store, year, month):
    first, last = dates.month_range(year, month)
    return period_total(store, first, last)


# 담당: 기능 3(류훈태)
def month_over_month(store, month):
    """전월 대비. 돌려주는 값: (이번 달, 지난달, 증감, 증감률 % 또는 None)"""
    year, mon = dates.parse_month(month)
    prev_year, prev_mon = dates.prev_month(year, mon)
    this_total = _month_sum(store, year, mon)
    last_total = _month_sum(store, prev_year, prev_mon)
    change = this_total - last_total
    if last_total == 0:
        return this_total, last_total, change, None
    # 증감률(%)은 정수로 사사오입한다(0 에서 먼 쪽으로). 소수 계산 오차를 피하려고 정수로만 계산.
    sign = 1 if change >= 0 else -1
    percent = sign * ((abs(change) * 200 + last_total) // (2 * last_total))
    return this_total, last_total, change, percent


# 담당: 기능 3(류훈태)
def weekday_totals(store, start, end):
    """요일별 합계. {'월': 합계, ..., '일': 합계} — 7개 요일을 월~일 순서로 모두 담는다(지출 없으면 0)."""
    totals = {name: 0 for name in WEEKDAYS}
    for e in expenses_in(store, start, end):
        totals[WEEKDAYS[dates.parse(e["date"]).weekday()]] += e["amount"]
    return totals


# 담당: 기능 3(류훈태)
def week_totals(store, start, end):
    """주(월요일 시작)별 합계. {'YYYY-MM-DD(그 주 월요일)': 합계}"""
    first = dates.parse(start)
    last = dates.parse(end)
    if first > last:
        return {}
    monday = first - dt.timedelta(days=first.weekday())
    totals = {}
    while monday <= last:
        totals[dates.fmt(monday)] = 0
        monday += dt.timedelta(days=7)
    for e in expenses_in(store, start, end):
        d = dates.parse(e["date"])
        totals[dates.fmt(d - dt.timedelta(days=d.weekday()))] += e["amount"]
    return totals


# 담당: 기능 3(류훈태)
def top_expenses(store, start, end, n=5):
    """기간에서 금액이 큰 지출 n 건(지출 dict 그대로). 금액 큰 순, 같으면 날짜·번호 순. 삭제된 지출은 뺀다."""
    if n <= 0:
        return []
    ranked = sorted(expenses_in(store, start, end), key=lambda e: (-e["amount"], e["date"], e["id"]))
    return ranked[:n]


# 담당: 기능 3(류훈태)
def biggest_day(store, start, end):
    """지출 합계가 가장 큰 날. 돌려주는 값: (날짜 'YYYY-MM-DD', 그날 합계). 지출이 없으면 None. 합계가 같으면 빠른 날짜."""
    by_day = {}
    for e in expenses_in(store, start, end):
        day = dates.fmt(e["date"])
        by_day[day] = by_day.get(day, 0) + e["amount"]
    if not by_day:
        return None
    day = min(by_day, key=lambda d: (-by_day[d], d))
    return day, by_day[day]


def month_report(store, month):
    raise NotImplementedError("이 함수를 구현한다")


def save_report(text, path):
    """보고서를 텍스트 파일(.txt)로 저장한다."""
    raise NotImplementedError("이 함수를 구현한다")


# 담당: 기능 3(류훈태)
def search(store, start=None, end=None, person=None, min_amount=None, max_amount=None, word=None):
    """지출 검색. 기간, 사람(낸 사람이거나 참여자), 금액 범위, 메모 낱말로 찾는다. 삭제된 지출은 빼고 날짜순."""
    found = expenses_in(store, start or "0001-01-01", end or "9999-12-31")
    if person is not None:
        found = [e for e in found if e["payer"] == person or person in e["members"]]
    if min_amount is not None:
        found = [e for e in found if e["amount"] >= money.to_won(min_amount)]
    if max_amount is not None:
        found = [e for e in found if e["amount"] <= money.to_won(max_amount)]
    if word:
        found = [e for e in found if word in (e.get("memo") or "")]
    return found
