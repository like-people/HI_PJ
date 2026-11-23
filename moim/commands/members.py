"""명령 묶음 `member`(참여자 명부). 담당: 기능 1(add·leave·list), 팀 공동 작업 설정 파일(load).

add_parser 에서 하위 명령과 인자를 만들고, run 에서 하위 명령을 실행한다.
run 은 자료를 바꿨으면 True 를 돌려준다(통합 실행 틀이 그때만 저장한다).
인자 해석은 common/cliutil.py 의 _members(참여자), _weights(비율), _period(기간)를 쓴다.
"""

from ..common.textfmt import table
from ..features import expenses as feat

GROUP = 'member'


def add_parser(sub, period_args):
    grp = sub.add_parser(GROUP, help="참여자 명부").add_subparsers(dest="cmd")
    s = grp.add_parser("add", help="회원 추가")
    s.add_argument("name", help="이름")
    s.add_argument("--joined", required=True, help="가입일(YYYY-MM-DD)")
    # 예: s = grp.add_parser("list"); s.add_argument("--order", default="id")
    #     기간을 받는 명령은 period_args(s) 로 --month, --start, --end 를 붙인다.
    s = grp.add_parser("leave", help="회원 탈퇴(탈퇴일 당일까지 회원)")
    s.add_argument("name", help="이름")
    s.add_argument("--date", required=True, help="탈퇴일(YYYY-MM-DD)")
    s = grp.add_parser("load", help="명부 파일 읽기(설정의 members_file)")
    s.add_argument("--file", help="명부 파일(없으면 설정의 members_file)")
    grp.add_parser("list", help="명부 목록(명부 순서)")
    return grp


def run(c, args, cfg, store, out):
    if c == "add":
        member = feat.add_member(store, args.name, args.joined)
        out(f"회원을 추가했습니다: {member['name']} (가입일 {member['joined']})")
        return True
    # 예: if c == "list": ...; return False
    if c == "leave":
        member = feat.leave_member(store, args.name, args.date)
        out(f"탈퇴를 기록했습니다: {member['name']} (탈퇴일 {member['left']})")
        return True
    if c == "load":
        path = args.file or cfg.get("members_file", "members.txt")
        added, left, errors = feat.load_members_file(store, path)
        out(f"추가 {len(added)}명, 탈퇴 반영 {len(left)}명, 오류 {len(errors)}줄")
        for no, msg in errors:
            out(f"{no}번째 줄: {msg}")
        return bool(added or left)
    if c == "list":
        members = feat.list_members(store)
        if not members:
            out("명부에 회원이 없습니다.")
        else:
            rows = [(m["name"], m["joined"], m.get("left") or "-") for m in members]
            out(table(("이름", "가입일", "탈퇴일"), rows))
        return False
    out(f"아직 만들지 않은 명령입니다: {GROUP} {c or ''}".rstrip())
    return False