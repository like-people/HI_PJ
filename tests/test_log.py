import logging
import os
import shutil
import tempfile
import unittest
from datetime import datetime

from moim.common.log import get_logger


class LoggerTests(unittest.TestCase):
    def setUp(self):
        self.log_dir = tempfile.mkdtemp()

    def tearDown(self):
        logger = logging.getLogger("moim")
        for handler in logger.handlers[:]:
            if getattr(handler, "_moim_file_handler", False):
                logger.removeHandler(handler)
                handler.close()
        shutil.rmtree(self.log_dir, ignore_errors=True)

    def test_creates_daily_log_file(self):
        logger = get_logger(self.log_dir)
        logger.info("명령 실행 완료")

        filename = datetime.now().strftime("%Y-%m-%d") + ".log"
        path = os.path.join(self.log_dir, filename)

        self.assertTrue(os.path.isfile(path))
        with open(path, encoding="utf-8") as f:
            content = f.read()

        self.assertIn("명령 실행 완료", content)

    def test_records_error_message(self):
        logger = get_logger(self.log_dir)
        logger.error("오류: 자료 파일을 찾을 수 없습니다")

        filename = datetime.now().strftime("%Y-%m-%d") + ".log"
        path = os.path.join(self.log_dir, filename)

        with open(path, encoding="utf-8") as f:
            content = f.read()

        self.assertIn("오류: 자료 파일을 찾을 수 없습니다", content)

    def test_repeated_call_does_not_duplicate_records(self):
        logger1 = get_logger(self.log_dir)
        logger2 = get_logger(self.log_dir)

        logger1.info("중복 검사")

        filename = datetime.now().strftime("%Y-%m-%d") + ".log"
        path = os.path.join(self.log_dir, filename)

        with open(path, encoding="utf-8") as f:
            content = f.read()

        self.assertEqual(content.count("중복 검사"), 1)
        self.assertIs(logger1, logger2)


if __name__ == "__main__":
    unittest.main()
