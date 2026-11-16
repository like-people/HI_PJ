
"""로그. 날짜별 파일(logs/YYYY-MM-DD.log)에 실행 기록을 남긴다."""

import logging
import time
from pathlib import Path


class _DailyFileHandler(logging.Handler):
    """로그 발생 날짜에 해당하는 파일에 기록하는 핸들러."""

    def __init__(self, log_dir):
        super().__init__()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def emit(self, record):
        try:
            # 로그가 실제로 발생한 날짜를 기준으로 파일을 선택한다.
            log_date = time.strftime(
                "%Y-%m-%d",
                time.localtime(record.created),
            )
            log_path = self.log_dir / f"{log_date}.log"

            # UTF-8로 기록하여 한글이 깨지지 않도록 한다.
            message = self.format(record)

            with log_path.open("a", encoding="utf-8") as file:
                file.write(message + "\n")

        except Exception:
            self.handleError(record)


def get_logger(log_dir):
    """moim 공용 로거를 반환한다.

    로그 형식:
        YYYY-MM-DD HH:MM:SS LEVEL 메시지

    저장 위치:
        log_dir/YYYY-MM-DD.log
    """
    logger = logging.getLogger("moim")

    # DEBUG 이상의 로그를 받을 수 있도록 설정한다.
    logger.setLevel(logging.DEBUG)

    # 상위 로거로 로그가 전달되어 중복 출력되는 것을 방지한다.
    logger.propagate = False

    log_dir = Path(log_dir)

    # 기존에 등록된 우리 파일 핸들러를 확인한다.
    handlers = [
        handler
        for handler in logger.handlers
        if isinstance(handler, _DailyFileHandler)
    ]

    # 같은 디렉터리의 핸들러가 있으면 재사용한다.
    for handler in handlers:
        if handler.log_dir == log_dir:
            return logger

    # 로그 디렉터리가 변경되었다면 기존 파일 핸들러를 제거한다.
    for handler in handlers:
        logger.removeHandler(handler)
        handler.close()

    # 새 파일 핸들러 등록
    file_handler = _DailyFileHandler(log_dir)
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger
