"""로그. 담당: 팀 공동 작업 "로그"(류강현)."""

import logging
from datetime import datetime
from pathlib import Path


def get_logger(log_dir):
    """날짜별 로그 파일에 기록하는 로거를 반환한다."""
    logger = logging.getLogger("moim")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    filename = datetime.now().strftime("%Y-%m-%d") + ".log"
    file_path = (log_path / filename).resolve()

    for handler in logger.handlers:
        if getattr(handler, "_moim_file_handler", False):
            if Path(handler.baseFilename) == file_path:
                return logger

    handler = logging.FileHandler(file_path, encoding="utf-8")
    handler._moim_file_handler = True
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)

    return logger
