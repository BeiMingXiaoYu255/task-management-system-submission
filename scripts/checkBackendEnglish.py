"""后端用户可见文案英文化检测脚本。

扫描 Backend/TaskManagementBackend、Backend/scripts 与 runServer.py 的 Python 源码，
用 AST 查找字符串常量中的中文；docstring 与注释不会被检查（允许保留中文注释/文档字符串）。

退出码：0 表示未发现中文用户可见字符串；1 表示存在，便于 CI/智能体验收。
用法：python scripts/checkBackendEnglish.py
"""

import ast
import re
import sys
from pathlib import Path

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
BACKEND_DIRECTORY = PROJECT_ROOT_DIRECTORY / "Backend"
TARGET_DIRECTORIES = [
    BACKEND_DIRECTORY / "TaskManagementBackend",
    BACKEND_DIRECTORY / "scripts",
]
TARGET_FILES = [BACKEND_DIRECTORY / "runServer.py"]
# 开发工具脚本：生成中文接口文档，不属于界面文案，跳过检查
EXCLUDED_FILE_NAMES = {"generateApiDocumentation.py"}
CHINESE_PATTERN = re.compile("[\u3400-\u9fff\uf900-\ufaff]")


def collectPythonFiles() -> list[Path]:
    """收集需要检查的 Python 文件列表。"""
    collectedFiles: list[Path] = []
    for targetDirectory in TARGET_DIRECTORIES:
        if targetDirectory.is_dir():
            collectedFiles.extend(sorted(targetDirectory.rglob("*.py")))
    collectedFiles.extend(path for path in TARGET_FILES if path.is_file())
    return [path for path in collectedFiles if path.name not in EXCLUDED_FILE_NAMES]


def collectDocstringNodes(tree: ast.AST) -> set[int]:
    """收集模块/类/函数 docstring 节点的 id，避免把文档字符串误报为用户文案。"""
    docstringIdentifiers: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstringIdentifiers.add(id(body[0].value))
    return docstringIdentifiers


def scanFile(filePath: Path) -> list[tuple[int, str]]:
    """扫描单个文件，返回 [(行号, 中文字符串片段)]。"""
    sourceText = filePath.read_text(encoding="utf-8")
    try:
        tree = ast.parse(sourceText)
    except SyntaxError:
        return []
    docstringIdentifiers = collectDocstringNodes(tree)
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstringIdentifiers:
            continue
        if CHINESE_PATTERN.search(node.value):
            snippet = " ".join(node.value.split())[:120]
            findings.append((node.lineno, snippet))
    return findings


def main() -> int:
    """执行扫描并输出结果。"""
    totalFindings = 0
    for filePath in collectPythonFiles():
        findings = scanFile(filePath)
        if not findings:
            continue
        totalFindings += len(findings)
        relativePath = filePath.relative_to(PROJECT_ROOT_DIRECTORY)
        for lineNumber, snippet in findings:
            print(f"{relativePath}:{lineNumber}: {snippet}")
    if totalFindings == 0:
        print("OK: backend user-facing strings contain no Chinese characters.")
        return 0
    print(f"Found {totalFindings} Chinese user-facing strings.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
