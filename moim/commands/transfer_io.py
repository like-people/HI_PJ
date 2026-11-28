"""명령 묶음 `io`(가져오기·내보내기). 담당: 기능 6.

add_parser 에서 하위 명령과 인자를 만들고, run 에서 하위 명령을 실행한다.
run 은 자료를 바꿨으면 True 를 돌려준다(통합 실행 틀이 그때만 저장한다).
인자 해석은 common/cliutil.py 의 _members(참여자), _weights(비율), _period(기간)를 쓴다.
"""

from ..common import dates, money
from ..common.cliutil import _period
from ..features import transfer_io as feat

GROUP = 'io'


def add_parser(sub, period_args):
    grp = sub.add_parser(GROUP, help="가져오기·내보내기").add_subparsers(dest="cmd")

    s = grp.add_parser("import", help="CSV 지출 가져오기")
    s.add_argument("file", help="가져올 CSV 파일")
    s.add_argument(
        "--preview",
        action="store_true",
        help="실제 등록 없이 가져오기 결과 미리 확인",
    )

    s.add_argument(
        "--map",
        action="append",
        default=[],
        metavar="열이름=필드",
        help="CSV 열 이름을 내부 필드에 연결(여러 번 지정 가능)",
    )

    s = grp.add_parser("export", help="지출 내보내기(파일 이름이 .json 이면 JSON, 아니면 CSV)")
    s.add_argument("file", help="내보낼 파일")
    period_args(s)
    s.add_argument("--category", help="이 분류만 내보내기(분류 없음은 미분류)")

    s = grp.add_parser("verify", help="내보낸 파일 합계가 기록 합계와 같은지 검사")
    s.add_argument("file", help="내보낸 파일(CSV 또는 JSON)")
    period_args(s)
    s.add_argument("--category", help="내보낼 때 준 분류")

    s = grp.add_parser("backup", help="모임 자료 전체 백업")
    s.add_argument("file", help="백업 파일 경로")

    s = grp.add_parser(
        "restore",
        help="백업 파일로 모임 전체 자료 복원 (현재 자료 덮어쓰기)",
    )
    s.add_argument("file", help="복원할 백업 파일 경로")

    s = grp.add_parser("merge", help="다른 모임 백업 자료를 현재 자료에 병합")
    s.add_argument("file", help="병합할 백업 파일 경로")

    s = grp.add_parser("total", help="파일의 지출 건수와 합계 확인")
    s.add_argument("file", help="확인할 CSV 또는 JSON 파일")

    s = grp.add_parser("roundtrip", help="내보낸 CSV와 원본 기록 비교 (CSV 전용)")
    s.add_argument("file", help="비교할 CSV 파일")
    period_args(s)
    s.add_argument("--category", help="이 분류만 비교(분류 없음은 미분류)")

    return grp


def _range(args):
    """기간을 주지 않으면 전체(None, None). 주면 'YYYY-MM-DD' 문자열 두 개."""
    if not (args.month or args.start or args.end):
        return None, None

    start, end = _period(args)

    if start > end:
        raise ValueError("시작일이 끝일보다 늦습니다")

    return dates.fmt(start), dates.fmt(end)


def run(c, args, cfg, store, out):
    if c == "import":
        mapping = {}
        valid_fields = {
            "date",
            "payer",
            "amount",
            "members",
            "weights",
            "category",
            "memo",
        }

        for item in args.map:
            if "=" not in item:
                raise ValueError(
                    f"--map 형식은 열이름=필드여야 합니다: {item}"
                )

            column, field = item.split("=", 1)
            column = column.strip()
            field = field.strip()

            if not column or not field:
                raise ValueError("--map의 열 이름과 필드는 비워둘 수 없습니다")

            if column in mapping:
                raise ValueError(f"중복된 CSV 열 매핑입니다: {column}")

            if field not in valid_fields:
                raise ValueError(
                    f"지원하지 않는 필드입니다: {field}"
                )

            mapping[column] = field

        result = feat.import_csv(
            store,
            args.file,
            mapping=mapping or None,
            preview=args.preview,
        )

        added = result["added"]
        duplicates = result["duplicates"]
        errors = result["errors"]

        label = "미리보기" if args.preview else "가져오기 완료"

        out(
            f"{label}: {args.file} "
            f"(인코딩 {result['encoding']}, "
            f"추가 {len(added)}건, "
            f"중복 {len(duplicates)}건, "
            f"오류 {len(errors)}줄)"
        )

        if duplicates:
            lines = ", ".join(map(str, duplicates))
            out(f"중복 의심 줄: {lines}")

        for line_no, reason in errors:
            out(f"{line_no}번째 줄: {reason}")

        if args.preview:
            out("미리보기이므로 실제 자료는 변경하지 않았습니다.")

        return bool(added) and not args.preview

    if c == "export":
        start, end = _range(args)
        export = feat.export_json if args.file.lower().endswith(".json") else feat.export_csv
        count, total = export(store, args.file, start, end, args.category)
        out(f"내보냈습니다: {args.file} ({count}건, 합계 {money.fmt(total)}원)")
        return False

    if c == "verify":
        start, end = _range(args)
        same, file_sum, record_sum = feat.verify_export(
            store, args.file, start, end, args.category
        )
        result = "같습니다" if same else "다릅니다"
        out(f"파일 합계 {money.fmt(file_sum)}원, 기록 합계 {money.fmt(record_sum)}원 → {result}")
        return False

    if c == "backup":
        feat.backup_all(store, args.file)
        out(f"백업했습니다: {args.file}")
        return False

    if c == "restore":
        feat.restore_all(store, args.file)
        out(f"복원했습니다: {args.file}")
        out("주의: 백업 파일의 모임 전체 자료로 현재 자료를 교체했습니다.")
        return True

    if c == "merge":
        members_before = len(store.data["members"])
        expenses_before = len(store.data["expenses"])

        report = {}
        added = feat.merge(store, args.file, report=report)

        members_added = len(store.data["members"]) - members_before

        out(
            f"병합했습니다: {args.file} "
            f"(회원 {members_added}명, 지출 {added}건 추가)"
        )

        skipped_members = [
            item for item in report.get("skipped", [])
            if item["kind"] == "member"
        ]
        skipped_expenses = [
            item for item in report.get("skipped", [])
            if item["kind"] == "expense"
        ]

        for item in skipped_members:
            out(
                f"회원 추가 건너뜀 ({item['id']}): "
                f"{item['reason']}"
            )

        for item in skipped_expenses:
            out(
                f"원본 지출 {item['id']}번 추가 건너뜀: "
                f"{item['reason']}"
            )

        duplicates = report.get("duplicates", [])
        if duplicates:
            original_ids = ", ".join(
                str(item["id"]) for item in duplicates
            )
            out(
                f"중복 의심 지출 {len(duplicates)}건도 등록했습니다. "
                f"(원본 지출 번호: {original_ids})"
            )

        expenses_added = len(store.data["expenses"]) - expenses_before
        return members_added > 0 or expenses_added > 0

    if c == "total":
        count, total = feat.file_total(args.file)
        out(f"파일: {args.file} ({count}건, 합계 {money.fmt(total)}원)")
        return False

    if c == "roundtrip":
        start, end = _range(args)
        different = feat.roundtrip_check(
            store, args.file, start, end, args.category
        )
        if different:
            out(f"원본 기록과 다른 지출 번호: {', '.join(map(str, different))}")
        else:
            out("원본 기록과 파일이 일치합니다.")
        return False

    out(f"아직 만들지 않은 명령입니다: {GROUP} {c or ''}".rstrip())
    return False
