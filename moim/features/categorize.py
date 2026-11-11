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
from ..common.queries import category_totals


def load_rules(path):
    raise NotImplementedError("이 함수를 구현한다")


def save_rules(path, rules):
    raise NotImplementedError("이 함수를 구현한다")


def add_rule(rules, category, keywords=None, priority=0, payer=None, min_amount=None, max_amount=None):
    raise NotImplementedError("이 함수를 구현한다")


def remove_rule(rules, index):
    raise NotImplementedError("이 함수를 구현한다")


def matches(rule, e):
    """규칙의 조건을 모두 만족하는가. 키워드는 하나라도 메모에 있으면 만족."""
    raise NotImplementedError("이 함수를 구현한다")


def classify(e, rules):
    """맞는 규칙 가운데 우선순위가 가장 높은 규칙의 분류. 같으면 먼저 등록한 규칙. 없으면 None."""
    raise NotImplementedError("이 함수를 구현한다")


def apply_rules(store, rules, preview=False):
    """전체 지출을 다시 분류한다. 직접 정한 분류(고정)는 건너뛴다.
    돌려주는 값: 바뀌는 목록 [(번호, 이전 분류, 새 분류)]. preview=True 면 실제로 바꾸지 않는다."""
    raise NotImplementedError("이 함수를 구현한다")


def set_category(store, eid, category):
    """분류를 직접 정한다. 다시 분류해도 바뀌지 않게 고정한다."""
    raise NotImplementedError("이 함수를 구현한다")


def unfix_category(store, eid):
    raise NotImplementedError("이 함수를 구현한다")


def uncategorized(store):
    raise NotImplementedError("이 함수를 구현한다")


def overlaps(rules):
    """같은 키워드가 서로 다른 분류의 규칙에 함께 있는 경우. [(규칙 번호 i, 규칙 번호 j, 겹친 키워드)]"""
    raise NotImplementedError("이 함수를 구현한다")


def summary(store, start, end):
    """분류별 건수·금액(공통 모듈의 분류 조회 사용)."""
    raise NotImplementedError("이 함수를 구현한다")
