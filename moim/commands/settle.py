"""명령 묶음 `settle`(정산). 담당: 기능 4.

add_parser 에서 하위 명령과 인자를 만들고, run 에서 하위 명령을 실행한다.
run 은 자료를 바꿨으면 True 를 돌려준다(통합 실행 틀이 그때만 저장한다).
인자 해석은 common/cliutil.py 의 _members(참여자), _weights(비율), _period(기간)를 쓴다.
"""

from types import SimpleNamespace

from ..common.cliutil import _period
from ..common.textfmt import table
from ..features import settle as feat

GROUP = 'settle'

BALANCE_HEADERS = ["이름", "낸 돈", "부담", "보낸 송금", "받은 송금", "잔액"]
COMPARE_HEADERS = ["이름", "이전 잔액", "지금 잔액", "차이"]


def add_parser(sub, period_args):
    grp = sub.add_parser(GROUP, help="정산").add_subparsers(dest="cmd")

    s = grp.add_parser("balance", help="사람마다 낸 돈·부담·송금·잔액과 잔액 합계")
    period_args(s)

    s = grp.add_parser("lock", help="정산 확정(이 기간의 지출은 더 이상 추가·수정·삭제할 수 없음)")
    period_args(s)

    grp.add_parser("locks", help="확정한 기간 목록")

    s = grp.add_parser("transfer", help="이미 보낸 송금 기록(부분 정산)")
    s.add_argument("--date", required=True, help="송금한 날(YYYY-MM-DD)")
    s.add_argument("--from", dest="frm", required=True, help="보낸 사람")
    s.add_argument("--to", required=True, help="받은 사람")
    s.add_argument("--amount", required=True, help="송금액")

    s = grp.add_parser("compare", help="정산 결과를 이전 정산과 비교(사람마다 이전 잔액·지금 잔액·차이)")
    period_args(s)
    s.add_argument("--prev-month", help="이전 정산 달(YYYY-MM)")
    s.add_argument("--prev-start", help="이전 정산 시작일(YYYY-MM-DD)")
    s.add_argument("--prev-end", help="이전 정산 끝일(YYYY-MM-DD)")
    return grp


def run(c, args, cfg, store, out):
    if c == "balance":
        start, end = _period(args)
        rows = feat.balances(store, start, end)
        if not rows:
            out("정산할 지출이 없습니다")
        else:
            body = [[name, r["paid"], r["owed"], r["sent"], r["received"], r["balance"]]
                    for name, r in rows.items()]
            out(table(BALANCE_HEADERS, body, numeric={1, 2, 3, 4, 5}))
        total = feat.balance_sum(rows)
        out(f"잔액 합계: {total:,}")
        if total != 0:
            out("경고: 잔액 합계가 0이 아닙니다. 자료를 확인하십시오")
        return False

    if c == "lock":
        start, end = _period(args)
        before = len(store.data["locks"])
        lock = feat.lock_period(store, start, end)
        if len(store.data["locks"]) == before:
            out(f"이미 확정한 기간입니다: {lock['start']} ~ {lock['end']}")
            return False
        out(f"정산을 확정했습니다: {lock['start']} ~ {lock['end']}")
        return True

    if c == "locks":
        locks = store.data.get("locks", [])
        if not locks:
            out("확정한 기간이 없습니다")
        else:
            body = [[lk["start"], lk["end"]] for lk in sorted(locks, key=lambda lk: (lk["start"], lk["end"]))]
            out(table(["시작일", "끝일"], body))
        return False

    if c == "transfer":
        t = feat.record_transfer(store, args.date, args.frm, args.to, args.amount)
        out(f"송금을 기록했습니다: {t['date']} {t['from']} → {t['to']} {t['amount']:,}원")
        return True

    if c == "compare":
        start, end = _period(args)
        if not (args.prev_month or (args.prev_start and args.prev_end)):
            raise ValueError("이전 기간을 지정하십시오(--prev-month YYYY-MM 또는 --prev-start, --prev-end)")
        # 이전 기간도 지금 기간과 같은 규칙(_period)으로 해석한다.
        prev = SimpleNamespace(month=args.prev_month, start=args.prev_start, end=args.prev_end)
        prev_start, prev_end = _period(prev)
        result = feat.compare(feat.balances(store, prev_start, prev_end), feat.balances(store, start, end))
        out(f"이전: {prev_start} ~ {prev_end} / 지금: {start} ~ {end}")
        if not result:
            out("비교할 정산이 없습니다")
            return False
        # 순서·차이 방향은 규격 4-4 4번(지금 명부 순서 → 이전에만 있는 사람, 차이 = 지금 - 이전). 차이 합도 0이다.
        body = [[name, before, now, diff] for name, (before, now, diff) in result.items()]
        total = ["합계"] + [sum(r[i] for r in body) for i in (1, 2, 3)]
        out(table(COMPARE_HEADERS, body, total=total, numeric={1, 2, 3}))
        return False

    out(f"아직 만들지 않은 명령입니다: {GROUP} {c or ''}".rstrip())
    return False
