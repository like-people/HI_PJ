"""명령 묶음 `report`(월별·기간 보고서). 담당: 기능 3.

add_parser 에서 하위 명령과 인자를 만들고, run 에서 하위 명령을 실행한다.
run 은 자료를 바꿨으면 True 를 돌려준다(통합 실행 틀이 그때만 저장한다).
인자 해석은 common/cliutil.py 의 _members(참여자), _weights(비율), _period(기간)를 쓴다.
"""

from ..common import dates, money
from ..common.cliutil import _period
from ..common.queries import category_totals, expenses_in
from ..common.textfmt import bar_chart, table
from ..features import report as feat

GROUP = 'report'


def add_parser(sub, period_args):
    grp = sub.add_parser(GROUP, help="월별·기간 보고서").add_subparsers(dest="cmd")

    s = grp.add_parser("month", help="한 달 보고서")
    s.add_argument("month", help="YYYY-MM")
    s.add_argument("--save", metavar="파일.txt", help="화면 대신 텍스트 파일(.txt)로 저장")

    s = grp.add_parser("period", help="기간 보고서")
    period_args(s)
    s.add_argument("--save", metavar="파일.txt", help="화면 대신 텍스트 파일(.txt)로 저장")

    s = grp.add_parser("monthly", help="달별 합계")
    s.add_argument("start_month", help="YYYY-MM")
    s.add_argument("end_month", help="YYYY-MM")

    s = grp.add_parser("weekday", help="요일별 합계")
    period_args(s)

    s = grp.add_parser("week", help="주별 합계(월요일 시작)")
    period_args(s)

    s = grp.add_parser("top", help="금액이 큰 지출")
    period_args(s)
    s.add_argument("-n", "--count", type=int, default=5, help="보여 줄 건수(기본 5)")

    s = grp.add_parser("search", help="지출 검색")
    period_args(s)
    s.add_argument("--person", help="낸 사람이거나 참여자")
    s.add_argument("--min-amount", help="이 금액 이상")
    s.add_argument("--max-amount", help="이 금액 이하")
    s.add_argument("--word", help="메모에 들어 있는 낱말")
    return grp


def _expense_table(items):
    rows = [[e["date"], e["id"], e["payer"], e.get("memo") or "", e["amount"]] for e in items]
    return table(["날짜", "번호", "낸 사람", "메모", "금액"], rows,
                 total=["합계", "", "", "", sum(e["amount"] for e in items)], numeric={4})


def _period_text(store, start, end):
    first, last = dates.fmt(start), dates.fmt(end)
    lines = [f"기간 보고서 ({first} ~ {last})", ""]
    summary = feat.period_summary(store, first, last)
    if not summary["total"]:
        lines.append("이 기간에는 지출이 없습니다.")
        return "\n".join(lines)
    count = len(expenses_in(store, first, last))
    lines.append(f"합계: {money.fmt(summary['total'])}원 ({count}건)")
    cats = category_totals(store, first, last)
    lines += ["", "[분류별]", table(["분류", "건수", "금액"],
                                  [[name, v["count"], v["amount"]] for name, v in cats.items()],
                                  total=["합계", count, summary["total"]], numeric={1, 2})]
    lines += ["", bar_chart(summary["by_category"])]
    lines += ["", "[사람별 낸 돈]", table(["이름", "낸 돈"], [[n, v] for n, v in summary["by_person"].items()], numeric={1})]
    lines += ["", "[요일별]", bar_chart(feat.weekday_totals(store, first, last))]
    return "\n".join(lines)


def _show(text, args, out):
    """--save 가 있으면 파일로 저장하고 알리고, 없으면 화면에 보인다."""
    if args.save:
        out(f"저장했습니다: {feat.save_report(text, args.save)}")
    else:
        out(text)


def _range(args):
    first, last = _period(args)
    return dates.fmt(first), dates.fmt(last)


def run(c, args, cfg, store, out):
    if c == "month":
        _show(feat.month_report(store, args.month), args, out)
    elif c == "period":
        _show(_period_text(store, *_period(args)), args, out)
    elif c == "monthly":
        totals = feat.monthly_totals(store, args.start_month, args.end_month)
        if not totals:
            raise ValueError("시작 달이 끝 달보다 늦습니다")
        out(table(["달", "합계"], list(totals.items()), total=["합계", sum(totals.values())], numeric={1}))
        out(bar_chart(totals))
    elif c == "weekday":
        out(bar_chart(feat.weekday_totals(store, *_range(args))))
    elif c == "week":
        totals = feat.week_totals(store, *_range(args))
        if not totals:
            raise ValueError("시작일이 끝일보다 늦습니다")
        out(table(["주(월요일)", "합계"], list(totals.items()), numeric={1}))
    elif c == "top":
        items = feat.top_expenses(store, *_range(args), n=args.count)
        out(_expense_table(items) if items else "지출이 없습니다.")
    elif c == "search":
        start, end = _range(args) if args.month else (args.start, args.end)
        items = feat.search(store, start, end, args.person, args.min_amount, args.max_amount, args.word)
        out(_expense_table(items) if items else "찾은 지출이 없습니다.")
    else:
        out("사용법: report month|period|monthly|weekday|week|top|search  (자세한 것은 report <명령> --help)")
    return False
