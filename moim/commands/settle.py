"""명령 묶음 `settle`(정산). 담당: 기능 4.

add_parser 에서 하위 명령과 인자를 만들고, run 에서 하위 명령을 실행한다.
run 은 자료를 바꿨으면 True 를 돌려준다(통합 실행 틀이 그때만 저장한다).
인자 해석은 common/cliutil.py 의 _members(참여자), _weights(비율), _period(기간)를 쓴다.
"""

from ..common.cliutil import _period
from ..common.textfmt import table
from ..features import settle as feat

GROUP = 'settle'

BALANCE_HEADERS = ["이름", "낸 돈", "부담", "보낸 송금", "받은 송금", "잔액"]


def add_parser(sub, period_args):
    grp = sub.add_parser(GROUP, help="정산").add_subparsers(dest="cmd")

    s = grp.add_parser("balance", help="사람마다 낸 돈·부담·송금·잔액과 잔액 합계")
    period_args(s)
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

    out(f"아직 만들지 않은 명령입니다: {GROUP} {c or ''}".rstrip())
    return False
