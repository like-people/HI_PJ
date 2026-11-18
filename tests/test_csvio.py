
import tempfile
import unittest
from pathlib import Path

from moim.common.csvio import detect_encoding


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


if __name__ == "__main__":
    unittest.main()
