# moim — 모임 회비·지출 정산 도구 (스켈레톤 코드)

이 파일은 팀 공동 작업 "사용 설명서" 담당이 완성한다(설치, 명령마다 사용 예와 출력 예).

## 지금 할 수 있는 것
```
python -m moim --help
python -m unittest discover -s tests      # 아직 비어 있는 기능의 테스트는 건너뜀(skipped)으로 나온다
python tools/check_imports.py             # 기능 파일끼리 불러 쓰면 실패
python tools/gen_data.py sample --month 2026-11   # 연습용 자료 만들기
```

## 폴더
```
moim/
  common/     공통 모듈. 규약 함수(rules, dates, money)와 빈 틀 함수(queries, ledger, textfmt 일부)
  features/   기능 6개. 파일 첫머리에 그 기능이 채울 공통 함수와 추가할 자료 항목이 적혀 있다
  commands/   기능별 명령 묶음. 그 기능 담당자가 하위 명령을 만든다
  cli.py      통합 실행 틀(최소판)
tests/        기본 동작 테스트(test_basic.py)
tools/        check_imports.py, gen_data.py
docs/         규약.md, 은행거래내역형식.md
```
