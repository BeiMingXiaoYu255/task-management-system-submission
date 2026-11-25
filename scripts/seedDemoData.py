"""演示数据种子脚本（项目根目录便捷入口）。

等价于：cd Backend && .venv/Scripts/python -m scripts.seedDemoData
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
BACKEND_DIRECTORY = PROJECT_ROOT_DIRECTORY / "Backend"
PYTHON_EXECUTABLE = BACKEND_DIRECTORY / ".venv" / "Scripts" / "python.exe"

if not PYTHON_EXECUTABLE.exists():
    PYTHON_EXECUTABLE = Path(sys.executable)

seedScriptPath = BACKEND_DIRECTORY / "scripts" / "seedDemoData.py"
result = subprocess.run([str(PYTHON_EXECUTABLE), str(seedScriptPath)], cwd=str(BACKEND_DIRECTORY))
sys.exit(result.returncode)
