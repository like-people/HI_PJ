"""명령 묶음 `cat`(분류 규칙). 담당: 기능 2.

add_parser 에서 하위 명령과 인자를 만들고, run 에서 하위 명령을 실행한다.
run 은 자료를 바꿨으면 True 를 돌려준다(통합 실행 틀이 그때만 저장한다).
인자 해석은 common/cliutil.py 의 _members(참여자), _weights(비율), _period(기간)를 쓴다.
"""

from ..common.cliutil import _members, _period
from ..features import categorize as feat

GROUP = 'cat'


def add_parser(sub, period_args):
    grp = sub.add_parser(GROUP, help="분류 규칙").add_subparsers(dest="cmd")

    grp.add_parser("rules", help="규칙 목록")

    s = grp.add_parser("add-rule", help="규칙 추가")
    s.add_argument("category")
    s.add_argument("--keywords", default="", help="키워드를 ;로 구분")
    s.add_argument("--priority", type=int, default=0)
    s.add_argument("--payer")
    s.add_argument("--min-amount", type=int)
    s.add_argument("--max-amount", type=int)

    s = grp.add_parser("remove-rule", help="규칙 삭제(목록의 번호)")
    s.add_argument("index", type=int)

    s = grp.add_parser("apply", help="전체 지출 다시 분류")
    s.add_argument("--preview", action="store_true", help="바꾸지 않고 미리 보기")

    s = grp.add_parser("set", help="분류를 직접 정함(고정)")
    s.add_argument("id", type=int)
    s.add_argument("category")

    s = grp.add_parser("unfix", help="직접 정한 분류의 고정 풀기")
    s.add_argument("id", type=int)

    grp.add_parser("uncategorized", help="분류가 없는 지출")
    grp.add_parser("overlaps", help="겹치는 키워드")

    s = grp.add_parser("summary", help="분류별 건수·금액")
    period_args(s)
    return grp


def _rules_path(cfg):
    return cfg.get("rules", "rules.json")


def run(c, args, cfg, store, out):
    path = _rules_path(cfg)

    if c == "rules":
        rules = feat.load_rules(path)
        if not rules:
            out("규칙이 없습니다")
        for i, r in enumerate(rules, 1):
            line = f"{i}. {r['category']} | 키워드: {';'.join(r.get('keywords') or [])} | 우선순위 {r.get('priority', 0)}"
            if r.get("payer"):
                line += f" | 낸 사람 {r['payer']}"
            if r.get("min_amount") is not None:
                line += f" | {r['min_amount']:,}원 이상"
            if r.get("max_amount") is not None:
                line += f" | {r['max_amount']:,}원 이하"
            out(line)
        return False

    if c == "add-rule":
        rules = feat.load_rules(path)
        feat.add_rule(rules, args.category, _members(args.keywords), args.priority,
                      args.payer, args.min_amount, args.max_amount)
        feat.save_rules(path, rules)
        out(f"규칙을 추가했습니다: {args.category}")
        return False

    if c == "remove-rule":
        rules = feat.load_rules(path)
        if not 1 <= args.index <= len(rules):
            raise ValueError(f"없는 규칙 번호입니다: {args.index}")
        removed = feat.remove_rule(rules, args.index - 1)
        feat.save_rules(path, rules)
        out(f"규칙을 삭제했습니다: {removed['category']}")
        return False

    if c == "apply":
        rules = feat.load_rules(path)
        changes = feat.apply_rules(store, rules, preview=args.preview)
        for eid, old, new in changes:
            out(f"{eid}번: {old} -> {new}")
        out(f"{len(changes)}건 {'바뀔 예정' if args.preview else '바꿨습니다'}")
        return bool(changes) and not args.preview

    if c == "set":
        feat.set_category(store, args.id, args.category)
        out(f"{args.id}번 분류를 {args.category}(으)로 정했습니다")
        return True

    if c == "unfix":
        feat.unfix_category(store, args.id)
        out(f"{args.id}번 분류 고정을 풀었습니다")
        return True

    if c == "uncategorized":
        items = feat.uncategorized(store)
        if not items:
            out("분류가 없는 지출이 없습니다")
        for e in items:
            out(f"{e['id']}번 {e['date']} {e['payer']} {e['amount']:,}원 {e.get('memo') or ''}".rstrip())
        return False

    if c == "overlaps":
        found = feat.overlaps(feat.load_rules(path))
        if not found:
            out("겹치는 키워드가 없습니다")
        for i, j, k in found:
            out(f"규칙 {i + 1}번과 {j + 1}번이 키워드 '{k}'를 함께 씁니다")
        return False

    if c == "summary":
        start, end = _period(args)
        for name, v in feat.summary(store, start, end).items():
            out(f"{name} {v['count']}건 {v['amount']:,}원")
        return False

    out("사용법: moim cat rules|add-rule|remove-rule|apply|set|unfix|uncategorized|overlaps|summary")
    return False