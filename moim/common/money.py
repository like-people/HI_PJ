"""금액 규칙: 원 단위 정수, 사사오입, 나머지 1원 배분."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def to_won(value):
    """금액 입력(문자열·숫자)을 원 단위 정수로 바꾼다. 소수점은 사사오입한다.

    예: "36,000" -> 36000, "1234.5" -> 1235, 2.5 -> 3
    """
    if isinstance(value, bool):
        raise ValueError(f"금액 형식이 잘못되었습니다: {value}")
    text = str(value).replace(",", "").replace("원", "").strip()
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"금액 형식이 잘못되었습니다: {value}") from None
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def remainder_order(members, payer=None):
    """나머지 1원을 받을 순서. 낸 사람이 참여자이면 맨 앞, 나머지는 목록 순서."""
    order = list(members)
    if payer in order:
        order.remove(payer)
        order.insert(0, payer)
    return order


def split(amount, members, payer=None, weights=None):
    """금액을 참여자에게 나눈다. 돌려주는 값: {이름: 부담액}. 합계는 항상 amount 와 같다.

    weights: {이름: 정수 비율}. 없으면 모두 1(균등). 예: {"A": 2, "B": 1, "C": 1}
    각자 몫은 비율대로 나눈 뒤 원 미만을 버리고, 남는 원은 remainder_order 순서로 1원씩 준다.
    """
    if not members:
        raise ValueError("나눌 사람이 없습니다")
    if amount < 0:
        raise ValueError("금액은 음수일 수 없습니다")
    if weights:
        raise NotImplementedError("비율 분배는 기능 4 담당이 구현한다")
    w = {m: 1 for m in members}
    total_w = sum(w.values())
    shares = {m: amount * w[m] // total_w for m in members}
    rest = amount - sum(shares.values())
    order = remainder_order(members, payer)
    i = 0
    while rest > 0:
        shares[order[i % len(order)]] += 1
        rest -= 1
        i += 1
    return shares


def fmt(amount):
    """천 단위 쉼표 표기. 예: 36000 -> '36,000'"""
    return f"{amount:,}"
