"""명령행 인자 해석 도우미. 모든 명령 묶음이 같은 형식으로 인자를 읽도록 한 곳에 둔다."""

from . import dates


def _members(text):
    """'김민수;이서연' -> ['김민수', '이서연']"""
    return [m.strip() for m in text.split(";") if m.strip()]


def _weights(text):
    """'김민수=2;이서연=1' -> {'김민수': 2, '이서연': 1}. 비어 있으면 None."""
    if not text:
        return None
    out = {}
    for part in text.split(";"):
        name, w = part.split("=")
        out[name.strip()] = int(w)
    return out


def _period(args):
    """--month 가 있으면 그달 1일~말일, 아니면 --start ~ --end."""
    if getattr(args, "month", None):
        return dates.month_range(*dates.parse_month(args.month))
    if not (args.start and args.end):
        raise ValueError("기간을 지정하십시오(--month YYYY-MM 또는 --start, --end)")
    return dates.parse(args.start), dates.parse(args.end)
