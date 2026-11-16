
"""CSV 가져오기·내보내기 공통 기능. 기능 6 담당."""

import csv


# 담당: 기능 6(류강현)
def detect_encoding(path):
    """UTF-8(BOM 포함)로 읽히면 utf-8-sig, 아니면 cp949. 둘 다 안 되면 ValueError."""
    with open(path, "rb") as file:
        raw = file.read()

    # UTF-8(BOM 포함) 우선 검사
    try:
        raw.decode("utf-8-sig")
        return "utf-8-sig"
    except UnicodeDecodeError:
        pass

    # UTF-8이 아니면 CP949 검사
    try:
        raw.decode("cp949")
        return "cp949"
    except UnicodeDecodeError:
        raise ValueError(
            "CSV 파일의 인코딩이 UTF-8 또는 CP949가 아닙니다."
        ) from None


# 담당: 기능 6(류강현)
def read_csv_rows(path, mapping=None, encoding=None):
    """CSV를 읽어 (인코딩, [(줄 번호, {필드: 값})])를 반환한다.

    mapping:
        {파일 열 이름: 필드 이름}

    encoding:
        직접 지정하지 않으면 자동 감지한다.
    """
    if encoding is None:
        encoding = detect_encoding(path)

    rows = []

    try:
        with open(path, "r", encoding=encoding, newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                line_number = reader.line_num

                if mapping is not None:
                    row = {
                        mapping.get(column, column): value
                        for column, value in row.items()
                        if column is not None
                    }

                rows.append((line_number, row))

    except (UnicodeDecodeError, csv.Error) as error:
        raise ValueError(
            f"CSV 파일을 읽을 수 없습니다: {error}"
        ) from error

    return encoding, rows
