"""명령 묶음 `budget`(예산·회비). 담당: 기능 5.

add_parser 에서 하위 명령과 인자를 만들고, run 에서 하위 명령을 실행한다.
run 은 자료를 바꿨으면 True 를 돌려준다(통합 실행 틀이 그때만 저장한다).
"""

from ..common import dates, money, textfmt
from ..features import budget as feat

GROUP = "budget"


def add_parser(sub, period_args):
    grp = sub.add_parser(GROUP, help="예산·회비").add_subparsers(dest="cmd")

    s = grp.add_parser("status", help="월 예산 상태")
    s.add_argument("--month", help="YYYY-MM (기본: 이번 달)")
    s.add_argument("--today", help="기준일 YYYY-MM-DD")

    s = grp.add_parser("category", help="분류별 예산 상태")
    s.add_argument("--month", help="YYYY-MM (기본: 이번 달)")

    s = grp.add_parser("forecast", help="월말 지출 예측")
    s.add_argument("--month", help="YYYY-MM (기본: 이번 달)")
    s.add_argument("--today", help="기준일 YYYY-MM-DD (기본: 오늘)")

    s = grp.add_parser("pay", help="회비 입금 기록")
    s.add_argument("member", help="회원 이름")
    s.add_argument("amount", help="입금액")
    s.add_argument("--date", help="입금일 YYYY-MM-DD (기본: 오늘)")
    s.add_argument("--memo", default="", help="메모")

    s = grp.add_parser("balance", help="모임 통장 잔고")
    s.add_argument("--until", help="기준일 YYYY-MM-DD")

    s = grp.add_parser("unpaid", help="월별 회비 미납자")
    s.add_argument("--month", help="YYYY-MM (기본: 이번 달)")

    s = grp.add_parser("table", help="예산 대비 실제 지출 표")
    s.add_argument("--month", help="YYYY-MM (기본: 이번 달)")

    return grp


def _month_of(args):
    return args.month or dates.parse(dates.today()).strftime("%Y-%m")


def _status_label(info):
    if info["budget"] is None:
        return "미설정"
    if info["over"]:
        return "초과"
    if info["warn"]:
        return "경고"
    return "정상"


def _cell(value):
    return "-" if value is None else value


def run(c, args, cfg, store, out):
    if c == "status":
        month = _month_of(args)
        info = feat.month_status(store, cfg, month, today=args.today)
        label = _status_label(info)
        if info["budget"] is None:
            out(f"{month} 월 예산: 미설정 | 지출 {money.fmt(info['spent'])}원")
        else:
            out(
                f"{month} 월 예산 {money.fmt(info['budget'])}원 | "
                f"지출 {money.fmt(info['spent'])}원 | "
                f"남은 금액 {money.fmt(info['remaining'])}원 | 상태: {label}"
            )
        return False

    if c == "category":
        month = _month_of(args)
        status = feat.category_status(store, cfg, month)
        if not status:
            out("분류별 예산이 설정되어 있지 않습니다")
            return False
        rows = [
            (
                cat,
                _cell(info["budget"]),
                info["spent"],
                _cell(info["remaining"]),
                _status_label(info),
            )
            for cat, info in status.items()
        ]
        out(textfmt.table(["분류", "예산", "지출", "남은 금액", "상태"], rows, numeric={1, 2, 3}))
        return False

    if c == "forecast":
        month = _month_of(args)
        today = args.today or dates.today()
        projected = feat.forecast(store, month, today)
        out(f"{month} 월말 예상 지출({dates.fmt(today)} 기준): {money.fmt(projected)}원")
        return False

    if c == "pay":
        pay_date = args.date or dates.today()
        payment = feat.record_payment(store, pay_date, args.member, args.amount, memo=args.memo)
        suffix = f" ({payment['memo']})" if payment["memo"] else ""
        out(
            f"회비 입금을 기록했습니다: {payment['date']} "
            f"{payment['member']} {money.fmt(payment['amount'])}원{suffix}"
        )
        return True

    if c == "balance":
        bal = feat.treasury_balance(store, until=args.until)
        if args.until is not None:
            out(f"모임 통장 잔고({dates.fmt(args.until)} 기준): {money.fmt(bal)}원")
        else:
            out(f"모임 통장 잔고: {money.fmt(bal)}원")
        return False

    if c == "unpaid":
        month = _month_of(args)
        if cfg.get("dues", {}).get("monthly") is None:
            out("월 회비가 설정되어 있지 않습니다")
            return False
        rows = feat.unpaid(store, cfg, month)
        if not rows:
            out(f"{month} 회비 미납자가 없습니다")
            return False
        out(textfmt.table(["이름", "낸 회비", "부족액"], rows, numeric={1, 2}))
        return False

    if c == "table":
        month = _month_of(args)
        rows = feat.budget_table(store, cfg, month)
        body = [(cat, _cell(b), spent, _cell(diff)) for cat, b, spent, diff in rows[:-1]]
        _label, tb, ts, td = rows[-1]
        foot = ("합계", _cell(tb), ts, _cell(td))
        out(textfmt.table(["분류", "예산", "실제", "차이"], body, total=foot, numeric={1, 2, 3}))
        return False

    out("사용법: moim budget status|category|forecast|pay|balance|unpaid|table")
    return False