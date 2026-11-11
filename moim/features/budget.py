"""기능 5. 예산·회비.

이 기능을 구현하려면 아래 공통 함수를 이 기능 담당자가 채운다(공통 모듈 병합 요청으로).
  - common/queries.py is_member_active — 그날 회원인가(공용: 기능 1의 지출 검사)
  - common/queries.py active_members — 그날 회원 목록
  - common/dates.py months_between — 두 달 사이의 달 목록(공용: 기능 3)
  - 은행 거래내역 가져오기는 기능 6이 채우는 common/csvio.py 의 read_csv_rows 를 쓴다

이 기능에 필요한 자료 항목은 common/store.py 의 EMPTY 에 이 기능 담당자가 추가한다.
  - 회비 입금(payments 목록)

아래 함수의 이름과 인자는 바꾸지 않는다(인수 테스트와 채점이 이 이름으로 실행된다).
필요하면 함수를 더 만들어도 된다. 다른 기능 파일은 불러 쓰지 않는다.
"""

from ..common import dates, ledger, money
from ..common.csvio import read_csv_rows
from ..common.queries import active_members, category_totals, period_total


def month_status(store, cfg, month, today=None):
    """이번 달 예산 상태. today 를 주면 그날까지의 지출만 센다."""
    raise NotImplementedError("이 함수를 구현한다")


def category_status(store, cfg, month):
    """분류별 예산 상태. {분류: {"budget", "spent", "remaining", "over", "warn"}}"""
    raise NotImplementedError("이 함수를 구현한다")


def forecast(store, month, today):
    """지금 속도로 쓰면 월말 합계가 얼마가 되는지. (오늘까지 지출 / 지난 일수) x 그달 일수."""
    raise NotImplementedError("이 함수를 구현한다")


def record_payment(store, date, member, amount, memo=""):
    """회비 입금을 기록한다."""
    raise NotImplementedError("이 함수를 구현한다")


def treasury_balance(store, until=None):
    """모임 통장 잔고 = 회비 입금 합계 - 지출 합계(until 날짜까지)."""
    raise NotImplementedError("이 함수를 구현한다")


def unpaid(store, cfg, month):
    """그달 회비 미납자. 그달 1일 또는 말일에 회원인 사람이 대상. [(이름, 낸 회비, 모자란 금액)]"""
    raise NotImplementedError("이 함수를 구현한다")


def dues_deduction(store, cfg, month):
    """회비를 덜 낸 사람에게 정산에서 차감할 금액. {이름: 모자란 회비}"""
    raise NotImplementedError("이 함수를 구현한다")


def budget_table(store, cfg, month):
    """예산 대비 실제 표 자료. [(분류, 예산, 실제, 차이)] 마지막 줄은 전체."""
    raise NotImplementedError("이 함수를 구현한다")


def suggest_budget(store, month):
    """다음 달 예산 제안: 그달을 포함한 최근 3개월 지출 평균(천 원 단위 올림)."""
    raise NotImplementedError("이 함수를 구현한다")

BANK_COLUMNS = ["거래일자", "거래시각", "적요", "출금액", "입금액", "잔액"]


def import_bank(store, path, treasurer):
    """가상 은행(Tarnwick 제휴 은행) 거래내역을 가져온다(docs/은행거래내역형식.md).
    출금 → 총무가 낸 지출(참여자: 그날의 회원 전원), 입금 → 적요의 이름으로 회비 입금.
    이미 들어간 거래(같은 날·같은 금액·같은 적요의 출금, 같은 날·같은 사람·같은 금액의 은행 입금)와
    파일 안에서 거래일자·거래시각·적요·금액·잔액이 모두 같은 줄은 중복으로 보고 건너뛴다.
    돌려주는 값: {"expenses": [번호], "payments": 건수, "duplicates": [줄 번호], "errors": [(줄 번호, 오류)]}"""
    raise NotImplementedError("이 함수를 구현한다")
