"""기능 2. 분류 규칙.

이 기능을 구현하려면 아래 공통 함수를 이 기능 담당자가 채운다(공통 모듈 병합 요청으로).
  - common/queries.py category_of — 지출의 분류 이름(공용: 기능 3·5·6)
  - common/queries.py category_totals — 분류별 건수·금액(공용: 기능 3·5)

이 기능에 필요한 자료 항목은 common/store.py 의 EMPTY 에 이 기능 담당자가 추가한다.
  - 직접 정한 분류의 고정 표시(category_fixed)

아래 함수의 이름과 인자는 바꾸지 않는다(인수 테스트와 채점이 이 이름으로 실행된다).
필요하면 함수를 더 만들어도 된다. 다른 기능 파일은 불러 쓰지 않는다.
"""

import json
import os
import tempfile
from ..common import money
from ..common.queries import category_of, category_totals, is_locked
from ..common.rules import UNCATEGORIZED


def load_rules(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_rules(path, rules):
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def add_rule(rules, category, keywords=None, priority=0, payer=None, min_amount=None, max_amount=None):
    rule = {
        "category": category,
        "keywords": list(keywords or []),
        "priority": priority,
        "payer": payer,
        "min_amount": min_amount,
        "max_amount": max_amount,
    }
    rules.append(rule)
    return rule


def remove_rule(rules, index):
    return rules.pop(index)


def matches(rule, e):
    """규칙의 조건을 모두 만족하는가. 키워드는 하나라도 메모에 있으면 만족."""
    keywords = rule.get("keywords") or []
    if keywords:
        memo = e.get("memo") or ""
        if not any(k in memo for k in keywords):
            return False
    if rule.get("payer") is not None and e.get("payer") != rule["payer"]:
        return False
    if rule.get("min_amount") is not None and e["amount"] < rule["min_amount"]:
        return False
    if rule.get("max_amount") is not None and e["amount"] > rule["max_amount"]:
        return False
    return True


def classify(e, rules):
    """맞는 규칙 가운데 우선순위가 가장 높은 규칙의 분류. 같으면 먼저 등록한 규칙. 없으면 None."""
    best = None
    for rule in rules:
        if not matches(rule, e):
            continue
        if best is None or rule.get("priority", 0) > best.get("priority", 0):
            best = rule
    return best["category"] if best else None


def _find(store, eid):
    for e in store.data["expenses"]:
        if e["id"] == eid:
            if e.get("deleted"):
                raise ValueError(f"삭제된 지출입니다: {eid}")
            return e
    raise ValueError(f"없는 지출 번호입니다: {eid}")


def _find_unlocked(store, eid):
    e = _find(store, eid)
    if is_locked(store, e["date"]):
        raise ValueError(f"정산이 확정된 기간의 지출은 분류를 바꿀 수 없습니다: {eid}")
    return e


def apply_rules(store, rules, preview=False):
    """전체 지출을 다시 분류한다. 직접 정한 분류(고정)와 정산이 확정된 기간의 지출은 건너뛴다.
    맞는 규칙이 없는 지출은 이전 분류를 그대로 둔다.
    돌려주는 값: 바뀌는 목록 [(번호, 이전 분류, 새 분류)]. preview=True 면 실제로 바꾸지 않는다."""
    changes = []
    for e in store.data["expenses"]:
        if e.get("deleted") or e.get("category_fixed") or is_locked(store, e["date"]):
            continue
        new = classify(e, rules)
        if new is None:
            continue
        old = category_of(e)
        if new != old:
            changes.append((e["id"], old, new))
            if not preview:
                e["category"] = new
    return changes


def set_category(store, eid, category):
    """분류를 직접 정한다. 다시 분류해도 바뀌지 않게 고정한다."""
    if not isinstance(category, str) or not category.strip():
        raise ValueError("분류 이름이 비어 있습니다")
    e = _find_unlocked(store, eid)
    category = category.strip()
    e["category"] = None if category == UNCATEGORIZED else category
    e["category_fixed"] = True


def unfix_category(store, eid):
    e = _find_unlocked(store, eid)
    e["category_fixed"] = False


def uncategorized(store):
    return [e for e in store.data["expenses"]
            if not e.get("deleted") and category_of(e) == UNCATEGORIZED]


def overlaps(rules):
    """같은 키워드가 서로 다른 분류의 규칙에 함께 있는 경우. [(규칙 번호 i, 규칙 번호 j, 겹친 키워드)]"""
    found = []
    for i in range(len(rules)):
        for j in range(i + 1, len(rules)):
            if rules[i]["category"] == rules[j]["category"]:
                continue
            for k in rules[i].get("keywords") or []:
                if k in (rules[j].get("keywords") or []):
                    found.append((i, j, k))
    return found


def summary(store, start, end):
    """분류별 건수·금액(공통 모듈의 분류 조회 사용)."""
    return category_totals(store, start, end)