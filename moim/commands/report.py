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

    s = grp.add_parser("period", help="기간 보고서")
    period_args(s)

    s = grp.add_parser("monthly", help="달별 합계")
    s.add_argument("start_month", help="YYYY-MM")
    s.add_argument("end_month", help="YYYY-MM")
    return grp


def _range(args):
    """기간 인자를 ('YYYY-MM-DD', 'YYYY-MM-DD') 로 바꾼다. 시작이 끝보다 늦으면 ValueError."""
    first, last = _period(args)
    if first > last:
        raise ValueError("시작일이 끝일보다 늦습니다")
    return dates.fmt(first), dates.fmt(last)


def _period_text(store, first, last):
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


def run(c, args, cfg, store, out):
    if c == "period":
        out(_period_text(store, *_range(args)))
    elif c == "monthly":
        totals = feat.monthly_totals(store, args.start_month, args.end_month)
        if not totals:
            raise ValueError("시작 달이 끝 달보다 늦습니다")
        out(table(["달", "합계"], list(totals.items()), total=["합계", sum(totals.values())], numeric={1}))
        out(bar_chart(totals))
    else:
        out("사용법: report period|monthly  (자세한 것은 report <명령> --help)")
    return False
