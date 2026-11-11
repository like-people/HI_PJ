"""모임 회비·지출 정산 도구(Tarnwick Labs).

패키지 구조
- moim.common   : 공통 모듈. 금액·날짜 규칙, 자료 저장, 조회. 모든 기능이 이것만 쓴다
- moim.features : 기능 6개. 기능 파일끼리는 서로 불러 쓰지 않는다
- moim.cli      : 명령행 통합 실행(python -m moim)
"""

__version__ = "1.0.0"
