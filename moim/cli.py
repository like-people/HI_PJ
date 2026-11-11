"""통합 실행 틀(최소판). 팀 공동 작업 "통합 실행" 담당이 완성한다.

지금 하는 일: 명령 묶음(moim/commands/*.py)을 붙이고, 설정을 읽고, 자료를 읽어 실행한 뒤 바뀌었으면 저장한다.
더할 일: init(기본 설정 파일 만들기), 오류를 "오류: 이유" 한 줄로 안내하고 종료 코드 1 돌려주기,
로그 남기기, 자료 파일이 깨졌을 때 복구 안내.
"""

import argparse

from .commands import budget, categorize, expenses, members, report, settle, transfer_io
from .common import config as cfgmod
from .common.store import Store

COMMANDS = [members, expenses, categorize, report, settle, budget, transfer_io]


def period_args(sp):
    sp.add_argument("--month", help="YYYY-MM")
    sp.add_argument("--start", help="YYYY-MM-DD")
    sp.add_argument("--end", help="YYYY-MM-DD")


def build_parser():
    p = argparse.ArgumentParser(prog="moim", description="모임 회비·지출 정산 도구")
    p.add_argument("--config", default="config.json", help="설정 파일 경로")
    sub = p.add_subparsers(dest="group", required=True)
    for mod in COMMANDS:
        mod.add_parser(sub, period_args)
    return p


def run(args, cfg, store, out=print):
    for mod in COMMANDS:
        if mod.GROUP == args.group:
            return mod.run(getattr(args, "cmd", None), args, cfg, store, out)
    raise ValueError(f"모르는 명령입니다: {args.group}")


def main(argv=None, out=print):
    args = build_parser().parse_args(argv)
    cfg = cfgmod.load(args.config)
    store = Store(cfg["data"]).load()
    if run(args, cfg, store, out):
        store.save()
    return 0
