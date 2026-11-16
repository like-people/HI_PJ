
"""명령 묶음 `io`(가져오기·내보내기). 담당: 기능 6."""

from ..features import transfer_io


GROUP = "io"


def add_parser(sub, period_args):
    grp = sub.add_parser(
        GROUP,
        help="가져오기·내보내기"
    ).add_subparsers(dest="cmd")

    # CSV 내보내기
    p = grp.add_parser("export-csv", help="CSV 파일로 내보내기")
    p.add_argument("path", help="저장할 CSV 파일 경로")
    period_args(p)
    p.add_argument("--category", help="분류 필터")

    # JSON 내보내기
    p = grp.add_parser("export-json", help="JSON 파일로 내보내기")
    p.add_argument("path", help="저장할 JSON 파일 경로")
    period_args(p)
    p.add_argument("--category", help="분류 필터")

    # CSV 가져오기
    p = grp.add_parser("import-csv", help="CSV 지출 가져오기")
    p.add_argument("path", help="가져올 CSV 파일 경로")
    p.add_argument("--encoding", help="파일 인코딩")
    p.add_argument(
        "--preview",
        action="store_true",
        help="실제 저장 없이 미리보기"
    )

    # 파일 합계
    p = grp.add_parser("file-total", help="파일의 건수와 금액 합계 확인")
    p.add_argument("path", help="확인할 파일 경로")

    # 내보내기 검증
    p = grp.add_parser("verify", help="파일과 원본의 합계 비교")
    p.add_argument("path", help="비교할 파일 경로")
    period_args(p)
    p.add_argument("--category", help="분류 필터")

    # 원본과 파일의 내용 비교
    p = grp.add_parser("roundtrip", help="내보낸 자료와 원본 비교")
    p.add_argument("path", help="비교할 파일 경로")
    period_args(p)
    p.add_argument("--category", help="분류 필터")

    # 전체 백업
    p = grp.add_parser("backup", help="전체 자료 백업")
    p.add_argument("path", help="백업 파일 경로")

    # 백업 복원
    p = grp.add_parser("restore", help="백업 자료 복원")
    p.add_argument("path", help="복원할 백업 파일 경로")

    # 다른 모임 자료 병합
    p = grp.add_parser("merge", help="다른 모임 자료 병합")
    p.add_argument("path", help="병합할 백업 파일 경로")

    return grp


def _get_period(args):
    """기간 인자가 있으면 시작일과 종료일을 반환한다."""
    if getattr(args, "month", None):
        from ..common.cliutil import _period
        return _period(args)

    start = getattr(args, "start", None)
    end = getattr(args, "end", None)

    if start or end:
        if not (start and end):
            raise ValueError("--start와 --end를 함께 지정해야 합니다")

        from ..common.cliutil import _period
        return _period(args)

    return None, None


def run(c, args, cfg, store, out):
    """하위 명령을 실행한다.

    자료를 변경했으면 True, 조회만 했으면 False를 반환한다.
    """

    if c in ("export-csv", "export-json", "verify", "roundtrip"):
        start, end = _get_period(args)
        category = getattr(args, "category", None)

    if c == "export-csv":
        count, total = transfer_io.export_csv(
            store,
            args.path,
            start,
            end,
            category
        )
        out(f"CSV 내보내기 완료: {count}건, {total:,}원")
        return False

    if c == "export-json":
        count, total = transfer_io.export_json(
            store,
            args.path,
            start,
            end,
            category
        )
        out(f"JSON 내보내기 완료: {count}건, {total:,}원")
        return False

    if c == "import-csv":
        result = transfer_io.import_csv(
            store,
            args.path,
            encoding=args.encoding,
            preview=args.preview
        )

        out(f"인코딩: {result['encoding']}")

        if args.preview:
            out(f"추가 예정 줄: {result['added']}")
            out(f"중복 줄: {result['duplicates']}")
        else:
            out(f"추가된 지출 번호: {result['added']}")
            out(f"중복 줄: {result['duplicates']}")

        for line, error in result["errors"]:
            out(f"{line}번째 줄 오류: {error}")

        if args.preview:
            out("미리보기 완료. 실제 자료는 변경되지 않았습니다.")
            return False

        return bool(result["added"])

    if c == "file-total":
        count, total = transfer_io.file_total(args.path)
        out(f"건수: {count}건")
        out(f"합계: {total:,}원")
        return False

    if c == "verify":
        same, file_sum, record_sum = transfer_io.verify_export(
            store,
            args.path,
            start,
            end,
            category
        )

        out(f"파일 합계: {file_sum:,}원")
        out(f"기록 합계: {record_sum:,}원")
        out("검증 결과: 일치" if same else "검증 결과: 불일치")
        return False

    if c == "roundtrip":
        different = transfer_io.roundtrip_check(
            store,
            args.path,
            start,
            end,
            category
        )

        if different:
            out(f"차이가 있는 지출 번호: {different}")
        else:
            out("원본과 파일의 내용이 같습니다.")

        return False

    if c == "backup":
        transfer_io.backup_all(store, args.path)
        out(f"백업 완료: {args.path}")
        return False

    if c == "restore":
        transfer_io.restore_all(store, args.path)
        out(f"복원 완료: {args.path}")
        return True

    if c == "merge":
        count = transfer_io.merge(store, args.path)
        out(f"병합 완료: 지출 {count}건 추가")
        return count > 0

    out(f"알 수 없는 명령입니다: {GROUP} {c or ''}".rstrip())
    return False
