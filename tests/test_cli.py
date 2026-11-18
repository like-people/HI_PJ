"""통합 실행의 오류 메시지와 종료 코드를 검증한다."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from moim.cli import main


class CLIErrorTests(unittest.TestCase):
    def setUp(self):
        work_dir = self.enterContext(tempfile.TemporaryDirectory())
        self.args = ["--config", str(Path(work_dir) / "config.json"), "exp"]
        self.output = []

    def test_value_error_flattens_multiple_lines(self):
        error = ValueError("참여자가 비어 있습니다\n이름을 입력하세요")
        with patch("moim.cli.run", side_effect=error):
            self.assertEqual(main(self.args, self.output.append), 1)
        self.assertEqual(self.output, ["오류: 참여자가 비어 있습니다 이름을 입력하세요"])

    def test_file_not_found(self):
        with patch("moim.cli.run", side_effect=FileNotFoundError("명부 파일이 없습니다")):
            self.assertEqual(main(self.args, self.output.append), 1)
        self.assertEqual(self.output, ["오류: 명부 파일이 없습니다"])

    def test_file_already_exists(self):
        with patch("moim.cli.run", side_effect=FileExistsError("설정 파일이 이미 있습니다")):
            self.assertEqual(main(self.args, self.output.append), 1)
        self.assertEqual(self.output, ["오류: 설정 파일이 이미 있습니다"])

    def test_success_returns_zero(self):
        with patch("moim.cli.run", return_value=False):
            self.assertEqual(main(self.args, self.output.append), 0)
        self.assertEqual(self.output, [])

    def test_unexpected_error_propagates(self):
        with patch("moim.cli.run", side_effect=TypeError("예상 밖 오류")):
            with self.assertRaisesRegex(TypeError, "예상 밖 오류"):
                main(self.args, self.output.append)
        self.assertEqual(self.output, [])


if __name__ == "__main__":
    unittest.main()
