"""CSV 읽기: 글자 인코딩 판별(UTF-8·CP949)과 열 이름 연결. 가져오기(기능 6)와 은행 거래내역 가져오기(기능 5)가 함께 쓴다."""

import csv


def detect_encoding(path):
    """UTF-8(BOM 포함)로 읽히면 utf-8-sig, 아니면 cp949. 둘 다 안 되면 ValueError."""
    raise NotImplementedError("기능 6 담당이 구현한다")


def read_csv_rows(path, mapping=None, encoding=None):
    """CSV 를 읽어 (인코딩, [(줄 번호, {필드: 값})]) 를 돌려준다. mapping: {파일 열 이름: 필드 이름}"""
    raise NotImplementedError("기능 6 담당이 구현한다")
