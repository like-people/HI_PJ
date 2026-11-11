"""명령 묶음 `report`(월별·기간 보고서). 담당: 기능 3.

add_parser 에서 하위 명령과 인자를 만들고, run 에서 하위 명령을 실행한다.
run 은 자료를 바꿨으면 True 를 돌려준다(통합 실행 틀이 그때만 저장한다).
인자 해석은 common/cliutil.py 의 _members(참여자), _weights(비율), _period(기간)를 쓴다.
"""

GROUP = 'report'


def add_parser(sub, period_args):
    grp = sub.add_parser(GROUP, help="보고서").add_subparsers(dest="cmd")
    # 예: s = grp.add_parser("list"); s.add_argument("--order", default="id")
    #     기간을 받는 명령은 period_args(s) 로 --month, --start, --end 를 붙인다.
    return grp


def run(c, args, cfg, store, out):
    # 예: if c == "list": ...; return False
    out(f"아직 만들지 않은 명령입니다: {GROUP} {c or ''}".rstrip())
    return False
