
"""CSV 읽기: 글자 인코딩 판별(UTF-8·CP949)과 열 이름 연결. 가져오기(기능 6)와 은행 거래내역 가져오기(기능 5)가 함께 쓴다."""

import csv


def detect_encoding(path):
    """UTF-8(BOM 포함)로 읽히면 utf-8-sig, 아니면 cp949. 둘 다 안 되면 ValueError."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            f.read()
        return "utf-8-sig"
    except UnicodeDecodeError:
        try:
            with open(path, "r", encoding="cp949") as f:
                f.read()
            return "cp949"
        except UnicodeDecodeError as e:
            raise ValueError("UTF-8 또는 CP949로 읽을 수 없는 파일입니다.") from e


def read_csv_rows(path, mapping=None, encoding=None):
    """CSV 를 읽어 (인코딩, [(줄 번호, {필드: 값})]) 를 돌려준다. mapping: {파일 열 이름: 필드 이름}"""
    raise NotImplementedError("기능 6 담당이 구현한다")

