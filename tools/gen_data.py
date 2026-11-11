"""연습용 자료를 만든다: 명부·지출 여러 줄 입력 파일(UTF-8), 은행 거래내역(CP949).

사용: python tools/gen_data.py <출력 폴더> [--month 2026-11] [--seed 1]
만드는 파일
- members.txt      : 이름,가입일 (명부)
- expenses.csv     : 날짜,낸 사람,금액,참여자1;참여자2,메모  (exp import-lines 로 입력)
- bank_YYYYMM.csv  : 가상 은행 거래내역(budget import-bank 로 입력, docs/은행거래내역형식.md)
"""

import argparse
import calendar
import csv
import os
import random

NAMES = ["김민수", "이서연", "박지훈", "최유진", "정하늘", "한도윤"]
MEMOS = [("회의 후 저녁", 30000, 90000), ("점심 김밥", 8000, 30000), ("세미나실 대관", 40000, 80000),
         ("택시비", 6000, 25000), ("간식 구입", 5000, 20000), ("현수막 제작", 30000, 60000),
         ("음료", 4000, 15000), ("문구 물품", 3000, 20000)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--month", default="2026-11")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--count", type=int, default=40)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    y, m = map(int, a.month.split("-"))
    last = calendar.monthrange(y, m)[1]
    os.makedirs(a.out, exist_ok=True)

    with open(os.path.join(a.out, "members.txt"), "w", encoding="utf-8") as f:
        for n in NAMES:
            f.write(f"{n},{y:04d}-{m:02d}-01\n")

    with open(os.path.join(a.out, "expenses.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for _ in range(a.count):
            day = rnd.randint(1, last)
            memo, lo, hi = rnd.choice(MEMOS)
            amount = rnd.randrange(lo, hi + 1, 100)
            members = rnd.sample(NAMES, rnd.randint(2, len(NAMES)))
            payer = rnd.choice(members)
            w.writerow([f"{y:04d}-{m:02d}-{day:02d}", payer, amount, ";".join(members), memo])

    balance = 500000
    with open(os.path.join(a.out, f"bank_{y:04d}{m:02d}.csv"), "w", encoding="cp949", newline="") as f:
        w = csv.writer(f)
        w.writerow(["거래일자", "거래시각", "적요", "출금액", "입금액", "잔액"])
        rows = []
        for n in NAMES:
            rows.append((rnd.randint(1, 10), n, 0, 20000))
        for _ in range(5):
            memo, lo, hi = rnd.choice(MEMOS)
            rows.append((rnd.randint(1, last), memo, rnd.randrange(lo, hi + 1, 100), 0))
        for day, memo, out_amt, in_amt in sorted(rows):
            balance += in_amt - out_amt
            w.writerow([f"{y:04d}.{m:02d}.{day:02d}", f"{rnd.randint(9, 21):02d}:{rnd.randint(0, 59):02d}",
                        memo, out_amt, in_amt, balance])
    print(f"만들었습니다: {a.out} (members.txt, expenses.csv, bank_{y:04d}{m:02d}.csv)")


if __name__ == "__main__":
    main()
