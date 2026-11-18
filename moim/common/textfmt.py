"""글자 표와 막대그래프. 보고서·지출 목록·정산·예산 명령이 함께 쓴다."""

import unicodedata

from . import money


def width(text):
    """화면 폭. 한글 등 넓은 글자는 2칸."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(text))


def pad(text, w, right=False):
    gap = w - width(text)
    return (" " * gap + str(text)) if right else (str(text) + " " * gap)


# 담당: 기능 3(류훈태)
def table(headers, rows, total=None, numeric=None):
    """표 문자열. numeric: 오른쪽 정렬할 열 번호 집합. 숫자는 천 단위 쉼표."""
    numeric = set(numeric or ())

    def cells(row):
        return [
            f"{v:,}" if i in numeric and isinstance(v, int) and not isinstance(v, bool) else str(v)
            for i, v in enumerate(row)
        ]

    head = [str(h) for h in headers]
    body = [cells(r) for r in rows]
    foot = cells(total) if total is not None else None
    every = [head] + body + ([foot] if foot else [])
    cols = max(len(r) for r in every)
    widths = [max(width(r[i]) for r in every if i < len(r)) for i in range(cols)]

    def line(r):
        return "  ".join(pad(r[i], widths[i], right=i in numeric) for i in range(len(r))).rstrip()

    sep = "-" * (sum(widths) + 2 * (cols - 1))
    out = [line(head), sep] + [line(r) for r in body]
    if foot:
        out += [sep, line(foot)]
    return "\n".join(out)


def bar_chart(data, bar_width=30, char="#"):
    """{이름: 값} 을 글자 막대그래프로."""
    raise NotImplementedError("기능 3 담당이 구현한다")
