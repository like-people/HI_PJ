"""기능 파일끼리 서로 import 하는지 검사한다. 있으면 종료 코드 1(자동 검사에서 병합을 막음).

사용: python tools/check_imports.py
"""

import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEATURES = os.path.join(ROOT, "moim", "features")


def feature_names():
    return {f[:-3] for f in os.listdir(FEATURES) if f.endswith(".py") and f != "__init__.py"}


def check():
    names = feature_names()
    problems = []
    for name in sorted(names):
        path = os.path.join(FEATURES, name + ".py")
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if node.level == 1 and mod in names:
                    targets.append(mod)
                if node.level == 1 and mod == "":
                    targets += [a.name for a in node.names if a.name in names]
                if mod.startswith("moim.features.") or (node.level == 2 and mod.startswith("features")):
                    targets.append(mod)
            if isinstance(node, ast.Import):
                targets += [a.name for a in node.names if a.name.startswith("moim.features.")]
            for t in targets:
                problems.append(f"{name}.py {node.lineno}번째 줄: 다른 기능({t})을 불러 씀")
    return problems


if __name__ == "__main__":
    found = check()
    for p in found:
        print(p)
    print("검사 통과: 기능 파일끼리 서로 불러 쓰지 않습니다" if not found else f"검사 실패: {len(found)}건")
    sys.exit(1 if found else 0)
