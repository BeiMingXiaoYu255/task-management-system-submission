#!/usr/bin/env bash
# 一键构建 Linux（AppImage/deb）与 macOS（dmg）安装包。
#
# 流程：前端构建 → 后端 PyInstaller 打包 → Tauri 资源 staging → tauri build → 产物复制到 release/
#
# 依赖（Ubuntu 22.04）：libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
#                     patchelf libssl-dev pkg-config python3 python3-pip
# 依赖（macOS）：Xcode Command Line Tools、python3
#
# 运行时说明：
#   Linux/macOS 安装包不内置数据库，需系统安装 MariaDB/MySQL 与 Redis；
#   安装后执行 packaging/setupSystemRuntime.sh 初始化数据库与账号，
#   也可通过环境变量 TASK_MANAGEMENT_DATABASE_URL / TASK_MANAGEMENT_REDIS_URL 覆盖连接地址。
#
# 用法：
#   ./scripts/buildInstallers.sh                       # 默认构建 AppImage + deb（Linux）或 dmg（macOS）
#   ./scripts/buildInstallers.sh --bundles dmg         # 指定 bundle 类型
#   ./scripts/buildInstallers.sh --skip-frontend-build --skip-backend-build

set -euo pipefail

# ===== 路径常量 =====
SCRIPT_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT_DIRECTORY="$(cd "${SCRIPT_DIRECTORY}/.." && pwd)"
FRONTEND_DIRECTORY="${REPO_ROOT_DIRECTORY}/Frontend"
BACKEND_DIRECTORY="${REPO_ROOT_DIRECTORY}/Backend"
TAURI_RESOURCES_DIRECTORY="${FRONTEND_DIRECTORY}/src-tauri/resources"
RELEASE_DIRECTORY="${REPO_ROOT_DIRECTORY}/release"

# ===== 参数解析 =====
BUNDLES=""
SKIP_FRONTEND_BUILD=0
SKIP_BACKEND_BUILD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundles)
      BUNDLES="$2"
      shift 2
      ;;
    --skip-frontend-build)
      SKIP_FRONTEND_BUILD=1
      shift
      ;;
    --skip-backend-build)
      SKIP_BACKEND_BUILD=1
      shift
      ;;
    --help|-h)
      grep '^#' "$0" | head -n 30
      exit 0
      ;;
    *)
      echo "未知参数：$1" >&2
      exit 1
      ;;
  esac
done

# 未指定 bundle 时按平台选择默认值
if [[ -z "${BUNDLES}" ]]; then
  case "$(uname -s)" in
    Darwin) BUNDLES="dmg" ;;
    *) BUNDLES="appimage,deb" ;;
  esac
fi

# ===== 工具函数 =====
logStep() {
  echo ""
  echo "===== $1 ====="
}

getPythonExecutable() {
  if [[ -x "${BACKEND_DIRECTORY}/.venv/bin/python" ]]; then
    echo "${BACKEND_DIRECTORY}/.venv/bin/python"
  else
    echo "python3"
  fi
}

# ===== 步骤 1：前端生产构建 =====
logStep "步骤 1/4：前端生产构建"
if [[ "${SKIP_FRONTEND_BUILD}" -eq 0 ]]; then
  (cd "${FRONTEND_DIRECTORY}" && npm run build)
else
  echo "已跳过前端构建"
fi
if [[ ! -f "${FRONTEND_DIRECTORY}/dist/index.html" ]]; then
  echo "错误：前端构建产物缺失 ${FRONTEND_DIRECTORY}/dist/index.html" >&2
  exit 1
fi

# ===== 步骤 2：后端 PyInstaller 打包 =====
logStep "步骤 2/4：后端可执行文件打包（PyInstaller onedir）"
PYTHON_EXECUTABLE="$(getPythonExecutable)"
echo "使用 Python：${PYTHON_EXECUTABLE}"
if [[ "${SKIP_BACKEND_BUILD}" -eq 0 ]]; then
  (cd "${BACKEND_DIRECTORY}" && "${PYTHON_EXECUTABLE}" buildBackend.py)
else
  echo "已跳过后端打包"
fi
if [[ ! -x "${BACKEND_DIRECTORY}/dist/runServer/runServer" ]]; then
  echo "错误：后端打包产物缺失 ${BACKEND_DIRECTORY}/dist/runServer/runServer" >&2
  exit 1
fi

# ===== 步骤 3：Tauri 资源 staging =====
logStep "步骤 3/4：资源 staging（后端 / 前端 / 系统运行时说明）"
rm -rf "${TAURI_RESOURCES_DIRECTORY}/backend" "${TAURI_RESOURCES_DIRECTORY}/runtime" "${TAURI_RESOURCES_DIRECTORY}/frontend"
mkdir -p "${TAURI_RESOURCES_DIRECTORY}/backend" "${TAURI_RESOURCES_DIRECTORY}/runtime" "${TAURI_RESOURCES_DIRECTORY}/frontend"

# 后端 onedir 产物（可执行文件名为 runServer，无扩展名）
cp -R "${BACKEND_DIRECTORY}/dist/runServer/." "${TAURI_RESOURCES_DIRECTORY}/backend/"

# Linux/macOS 使用系统 MariaDB/Redis：runtime 目录只放说明文件（安装后由 setupSystemRuntime.sh 初始化）
cat > "${TAURI_RESOURCES_DIRECTORY}/runtime/RUNTIME_README.md" <<'RUNTIME_DOC'
# Linux/macOS 运行时说明

本平台安装包不内置便携数据库，请使用系统安装的 MariaDB/MySQL 与 Redis：

1. 安装服务（Ubuntu/Debian）：
   sudo apt-get install -y mariadb-server redis-server
   （macOS：brew install mariadb redis && brew services start mariadb redis）
2. 初始化业务库与账号（仓库内提供脚本）：
   sudo bash packaging/setupSystemRuntime.sh
3. 应用默认连接 127.0.0.1:3307（不存在时自动尝试 3306）的 MariaDB 与 127.0.0.1:6380（不存在时尝试 6379）的 Redis；
   也可通过环境变量 TASK_MANAGEMENT_DATABASE_URL / TASK_MANAGEMENT_REDIS_URL 覆盖。
RUNTIME_DOC

# 前端静态资源（供局域网浏览器访问）
cp -R "${FRONTEND_DIRECTORY}/dist/." "${TAURI_RESOURCES_DIRECTORY}/frontend/"

# ===== 步骤 4：Tauri 打包 =====
logStep "步骤 4/4：Tauri 打包（bundles=${BUNDLES}）"
(cd "${FRONTEND_DIRECTORY}" && npx tauri build --bundles "${BUNDLES}")

# ===== 产物整理 =====
mkdir -p "${RELEASE_DIRECTORY}"
BUNDLE_OUTPUT_DIRECTORY="${FRONTEND_DIRECTORY}/src-tauri/target/release/bundle"
find "${BUNDLE_OUTPUT_DIRECTORY}" -maxdepth 2 -type f \( -name '*.AppImage' -o -name '*.deb' -o -name '*.dmg' -o -name '*.rpm' \) -exec cp -f {} "${RELEASE_DIRECTORY}/" \;

logStep "构建完成"
echo "产物目录：${RELEASE_DIRECTORY}"
ls -lh "${RELEASE_DIRECTORY}" || true
