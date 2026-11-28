import tempfile
import unittest
from pathlib import Path

from moim.common.csvio import detect_encoding, read_csv_rows


class TestDetectEncoding(unittest.TestCase):
    def test_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "utf8.csv"
            path.write_bytes("이름,금액\n철수,1000".encode("utf-8"))
            self.assertEqual(detect_encoding(path), "utf-8-sig")

    def test_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "utf8_bom.csv"
            path.write_bytes("이름,금액\n철수,1000".encode("utf-8-sig"))
            self.assertEqual(detect_encoding(path), "utf-8-sig")

    def test_cp949(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cp949.csv"
            path.write_bytes("이름,금액\n철수,1000".encode("cp949"))
            self.assertEqual(detect_encoding(path), "cp949")

    def test_invalid_encoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.csv"
            path.write_bytes(b"\x81")
            with self.assertRaises(ValueError):
                detect_encoding(path)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.csv"
            with self.assertRaises(FileNotFoundError):
                detect_encoding(path)

    def test_directory_path_reports_read_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(
                ValueError,
                "파일을 읽을 수 없습니다",
            ):
                detect_encoding(tmp)


class TestReadCsvRows(unittest.TestCase):
    def test_mapping_and_unmapped_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text(
                "이름,금액,비고\n 철수 , 1000 , 식비 \n",
                encoding="utf-8",
            )

            encoding, rows = read_csv_rows(
                path,
                mapping={"이름": "payer", "금액": "amount"},
            )

            self.assertEqual(encoding, "utf-8-sig")
            self.assertEqual(
                rows,
                [(2, {"payer": "철수", "amount": "1000", "비고": "식비"})],
            )

    def test_missing_and_empty_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text(
                "이름,금액,비고\n철수,,\n영희\n",
                encoding="utf-8",
            )

            _, rows = read_csv_rows(path)

            self.assertEqual(
                rows,
                [
                    (2, {"이름": "철수", "금액": "", "비고": ""}),
                    (3, {"이름": "영희", "금액": "", "비고": ""}),
                ],
            )

    def test_actual_line_number_with_multiline_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text(
                '이름,비고\n철수,"첫째 줄\n둘째 줄"\n영희,식비\n',
                encoding="utf-8",
            )

            _, rows = read_csv_rows(path)

            self.assertEqual(rows[0][0], 2)
            self.assertEqual(rows[1][0], 4)


    def test_actual_line_number_with_blank_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text(
                "이름,금액\n철수,1000\n\n영희,2000\n",
                encoding="utf-8",
            )

            _, rows = read_csv_rows(path)

            self.assertEqual(
                [line_number for line_number, _ in rows],
                [2, 4],
            )

    def test_actual_line_number_with_blank_lines_and_multiline_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text(
                '이름,비고\n\n철수,"첫째 줄\n둘째 줄"\n\n영희,식비\n',
                encoding="utf-8",
            )

            _, rows = read_csv_rows(path)

            self.assertEqual(
                [line_number for line_number, _ in rows],
                [3, 6],
            )

    def test_skip_blank_lines_before_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text(
                "\n\n이름,금액\n철수,1000\n영희,2000\n",
                encoding="utf-8",
            )

            _, rows = read_csv_rows(path)

            self.assertEqual(
                rows,
                [
                    (4, {"이름": "철수", "금액": "1000"}),
                    (5, {"이름": "영희", "금액": "2000"}),
                ],
            )


if __name__ == "__main__":
    unittest.main()
