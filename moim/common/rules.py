"""규약 값. docs/규약.md 와 반드시 같아야 한다. 값을 바꾸려면 교수 승인이 먼저다."""

# 금액은 원 단위 정수로만 저장한다
CURRENCY = "KRW"

# 소수점이 있는 금액은 사사오입한다(0.5 는 올림). 파이썬 기본 round() 는 쓰지 않는다
ROUNDING = "HALF_UP"

# 나눗셈에서 남는 1원은 지출을 낸 사람부터 1원씩, 이어서 참여자 목록 순서대로 배분한다
REMAINDER_ORDER = "PAYER_FIRST_THEN_LISTED"

# 기간은 시작일과 끝일을 모두 포함한다. 한 달은 1일부터 그달 말일까지다
PERIOD_START_INCLUSIVE = True
PERIOD_END_INCLUSIVE = True

# 날짜 표기
DATE_FORMAT = "%Y-%m-%d"
MONTH_FORMAT = "%Y-%m"

# 분류가 없는 지출의 표시 이름
UNCATEGORIZED = "미분류"
