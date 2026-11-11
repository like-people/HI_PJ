"""날짜·기간 규칙: YYYY-MM-DD, 기간은 시작일과 끝일을 모두 포함."""

import calendar
import datetime as dt

from .rules import DATE_FORMAT


def parse(value):
    """'2026-11-12' 형식의 문자열을 date 로 바꾼다. 없는 날짜면 ValueError."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dt.datetime.strptime(str(value).strip(), DATE_FORMAT).date()
    except ValueError:
        raise ValueError(f"날짜가 잘못되었습니다(YYYY-MM-DD, 실제 있는 날짜): {value}") from None


def fmt(value):
    return parse(value).strftime(DATE_FORMAT)


def parse_month(text):
    """'2026-11' -> (2026, 11)"""
    try:
        y, m = str(text).strip().split("-")
        y, m = int(y), int(m)
        if not 1 <= m <= 12:
            raise ValueError
        return y, m
    except ValueError:
        raise ValueError(f"달 형식이 잘못되었습니다(YYYY-MM): {text}") from None


def days_in_month(year, month):
    return calendar.monthrange(year, month)[1]


def month_range(year, month):
    """그달의 첫날과 말일. 기간 규칙상 둘 다 포함한다."""
    return dt.date(year, month, 1), dt.date(year, month, days_in_month(year, month))


def in_period(value, start, end):
    """value 가 start~end 기간 안에 있는가. 시작일·끝일 모두 포함."""
    d = parse(value)
    return parse(start) <= d <= parse(end)


def month_key(value):
    raise NotImplementedError("기능 6 담당이 구현한다")


def prev_month(year, month):
    return (year - 1, 12) if month == 1 else (year, month - 1)


def next_month(year, month):
    return (year + 1, 1) if month == 12 else (year, month + 1)


def months_between(start_ym, end_ym):
    """(y,m) 부터 (y,m) 까지 달 목록. 둘 다 포함."""
    raise NotImplementedError("기능 5 담당이 구현한다")


def today():
    return dt.date.today()
