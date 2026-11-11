"""로그. 팀 공동 작업 "로그" 담당이 날짜별 파일(logs/YYYY-MM-DD.log)에 남기도록 완성한다."""

import logging


def get_logger(log_dir):
    """지금은 아무 데도 기록하지 않는 로거를 돌려준다."""
    logger = logging.getLogger("moim")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger
