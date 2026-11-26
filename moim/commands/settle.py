"""명령 묶음 `settle`(정산). 담당: 기능 4.

add_parser 에서 하위 명령과 인자를 만들고, run 에서 하위 명령을 실행한다.
run 은 자료를 바꿨으면 True 를 돌려준다(통합 실행 틀이 그때만 저장한다).
인자 해석은 common/cliutil.py 의 _members(참여자), _weights(비율), _period(기간)를 쓴다.
"""

from ..common import dates
from ..common.cliutil import _members, _period
from ..common.textfmt import table
from ..features import settle as feat

GROUP = 'settle'

BALANCE_HEADERS = ["이름", "낸 돈", "부담", "보낸 송금", "받은 송금", "잔액"]
RECURRING_HEADERS = ["번호", "매월", "낸 사람", "금액", "참여자", "메모", "시작 달", "마지막으로 만든 달"]


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

    s = grp.add_parser("add-recurring", help="반복 지출 등록(매월 같은 날, 그달에 없는 날은 말일)")
    s.add_argument("--day", type=int, required=True, help="매월 며칠(1~31)")
    s.add_argument("--payer", required=True, help="낸 사람")
    s.add_argument("--amount", required=True, help="금액")
    s.add_argument("--members", required=True, help="참여자(김민수;이서연)")
    s.add_argument("--memo", default="", help="메모")
    s.add_argument("--start-month", required=True, help="처음 만들 달(YYYY-MM)")

    s = grp.add_parser("run-recurring", help="반복 지출 생성(아직 만들지 않은 달만)")
    s.add_argument("--until", help="이 날짜까지 만듦(YYYY-MM-DD, 없으면 오늘)")

    grp.add_parser("recurring", help="반복 지출 목록")
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

    if c == "add-recurring":
        rec = feat.add_recurring(store, args.day, args.payer, args.amount, _members(args.members),
                                 args.memo, args.start_month)
        out(f"반복 지출을 등록했습니다: {rec['id']}번 매월 {rec['day']}일 {rec['payer']} {rec['amount']:,}원 "
            f"({rec['start_month']}부터)")
        return True

    if c == "run-recurring":
        until = args.until or dates.today()
        before = [r.get("last_month") for r in store.data["recurring"]]
        created, skipped = feat.run_recurring_report(store, until)
        for e in created:
            out(f"지출을 만들었습니다: {e['id']}번 {e['date']} {e['payer']} {e['amount']:,}원 {e.get('memo', '')}".rstrip())
        # 규격 4-4 7번: 만들 수 없어 건너뛴 달은 이유와 함께 알린다.
        for rid, day, reason in skipped:
            out(f"건너뜀: 반복 {rid}번 {day} ({reason})")
        if not created and not skipped:
            out(f"{dates.fmt(until)}까지 새로 만들 반복 지출이 없습니다")
        # 건너뛴 달도 last_month 가 넘어가므로, 바뀐 것이 있으면 저장한다.
        return before != [r.get("last_month") for r in store.data["recurring"]]

    if c == "recurring":
        recs = store.data.get("recurring", [])
        if not recs:
            out("등록한 반복 지출이 없습니다")
        else:
            body = [[r["id"], f"{r['day']}일", r["payer"], r["amount"], ";".join(r["members"]), r.get("memo", ""),
                     r["start_month"], r.get("last_month") or "-"] for r in recs]
            out(table(RECURRING_HEADERS, body, numeric={3}))
        return False

    out(f"아직 만들지 않은 명령입니다: {GROUP} {c or ''}".rstrip())
    return False
