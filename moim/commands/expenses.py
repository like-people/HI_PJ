"""명령 묶음 `exp`(지출 입력·관리). 담당: 기능 1.

add_parser 에서 하위 명령과 인자를 만들고, run 에서 하위 명령을 실행한다.
run 은 자료를 바꿨으면 True 를 돌려준다(통합 실행 틀이 그때만 저장한다).
인자 해석은 common/cliutil.py 의 _members(참여자), _weights(비율), _period(기간)를 쓴다.
"""

import argparse

from ..common.cliutil import _members, _weights
from ..common.queries import category_of
from ..common.textfmt import table
from ..features import expenses

GROUP = 'exp'

def _expense_fields(parser, required=False):
    parser.add_argument("--date", required=required, help="지출일(YYYY-MM-DD)")
    parser.add_argument("--payer", required=required, help="낸 사람")
    parser.add_argument("--amount", required=required, help="지출 금액")
    parser.add_argument("--members", required=required, help="참여자(예: 김민수;이서연)")
    parser.add_argument("--memo", help="메모")
    parser.add_argument("--category", help="분류")

def add_parser(sub, period_args):
    grp = sub.add_parser(GROUP, help="지출 입력·관리").add_subparsers(dest="cmd")

    add = grp.add_parser("add", help="지출 추가")
    _expense_fields(add, required=True)
    add.set_defaults(memo="")
    add.add_argument("--weights", help="분담 비율(예: 김민수=2;이서연=1)")

    listing = grp.add_parser("list", help="지출 목록")
    listing.add_argument("--order", choices=("id", "date"), default="id", help="정렬 기준")

    edit = grp.add_parser("edit", help="지출 수정", argument_default=argparse.SUPPRESS)
    edit.add_argument("eid", type=int, help="지출 번호")
    _expense_fields(edit)
    weights = edit.add_mutually_exclusive_group()
    weights.add_argument("--weights", help="새 분담 비율(예: 김민수=2;이서연=1)")
    weights.add_argument("--equal", dest="weights", action="store_const", const=None,
                         help="균등 분배로 변경")

    delete = grp.add_parser("delete", help="지출 삭제")
    delete.add_argument("eid", type=int, help="지출 번호")
    return grp


def add_parser(sub, period_args):
    grp = sub.add_parser(GROUP, help="지출 입력·관리").add_subparsers(dest="cmd")

    add = grp.add_parser("add", help="지출 추가")
    _expense_fields(add, required=True)
    add.set_defaults(memo="")
    add.add_argument("--weights", help="분담 비율(예: 김민수=2;이서연=1)")

    listing = grp.add_parser("list", help="지출 목록")
    listing.add_argument("--order", choices=("id", "date"), default="id", help="정렬 기준")

    edit = grp.add_parser("edit", help="지출 수정", argument_default=argparse.SUPPRESS)
    edit.add_argument("eid", type=int, help="지출 번호")
    _expense_fields(edit)
    weights = edit.add_mutually_exclusive_group()
    weights.add_argument("--weights", help="새 분담 비율(예: 김민수=2;이서연=1)")
    weights.add_argument("--equal", dest="weights", action="store_const", const=None,
                         help="균등 분배로 변경")

    delete = grp.add_parser("delete", help="지출 삭제")
    delete.add_argument("eid", type=int, help="지출 번호")
    return grp


def run(c, args, cfg, store, out):
    if c == "add":
        expense, warnings = expenses.add_expense(
            store, args.date, args.payer, args.amount, _members(args.members),
            memo=args.memo, weights=_weights(args.weights), category=args.category,
        )
        out(f"{expense['id']}번 지출을 추가했습니다.")
        for warning in warnings:
            out(f"경고: {warning}")
        return True

    if c == "list":
        entries = expenses.list_expenses(store, order=args.order)
        if entries:
            rows = [
                (e["id"], e["date"], e["payer"], e["amount"], category_of(e),
                 ";".join(e["members"]), e.get("memo", ""))
                for e in entries
            ]
            out(table(("번호", "날짜", "낸 사람", "금액(원)", "분류", "참여자", "메모"),
                      rows, numeric={3}))
        else:
            out("등록된 지출이 없습니다.")
        return False

    if c == "edit":
        changes = {
            field: getattr(args, field)
            for field in ("date", "payer", "amount", "members", "memo", "weights", "category")
            if hasattr(args, field)
        }
        if not changes:
            raise ValueError("수정할 항목을 하나 이상 지정해 주세요")
        if "members" in changes:
            changes["members"] = _members(changes["members"])
        if "weights" in changes:
            changes["weights"] = _weights(changes["weights"])
        expenses.edit_expense(store, args.eid, **changes)
        out(f"{args.eid}번 지출을 수정했습니다.")
        return True

    if c == "delete":
        was_deleted = store.get_expense(args.eid).get("deleted", False)
        expenses.delete_expense(store, args.eid)
        if was_deleted:
            out(f"{args.eid}번 지출은 이미 삭제됐습니다.")
            return False
        out(f"{args.eid}번 지출을 삭제했습니다.")
        return True

    out(f"아직 만들지 않은 명령입니다: {GROUP} {c or ''}".rstrip())
    return False
