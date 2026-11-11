"""글자 표와 막대그래프. 보고서·지출 목록·정산·예산 명령이 함께 쓴다."""

import unicodedata

from . import money


def width(text):
    """화면 폭. 한글 등 넓은 글자는 2칸."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(text))


def pad(text, w, right=False):
    gap = w - width(text)
    return (" " * gap + str(text)) if right else (str(text) + " " * gap)


def table(headers, rows, total=None, numeric=None):
    """표 문자열. numeric: 오른쪽 정렬할 열 번호 집합. 숫자는 천 단위 쉼표."""
    raise NotImplementedError("기능 3 담당이 구현한다")


def bar_chart(data, bar_width=30, char="#"):
    """{이름: 값} 을 글자 막대그래프로."""
    raise NotImplementedError("기능 3 담당이 구현한다")
