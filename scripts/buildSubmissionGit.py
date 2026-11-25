"""Build a four-member, time-boxed Git history for submission (15-25 Nov 2026)."""

from __future__ import annotations

import argparse
import csv
import glob
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPOSITORY = PROJECT_ROOT.parent / "task-management-system-submission-git"
DELIVERABLES = PROJECT_ROOT / "deliverables" / "05_GitHistory"
DEFAULT_AUTHORS = {
    "A": ("Member A", "member.a@task-management.local"),
    "B": ("Member B", "member.b@task-management.local"),
    "C": ("Member C", "member.c@task-management.local"),
    "D": ("Member D", "member.d@task-management.local"),
}

COMMIT_PLAN = [
    ("2026-11-15", "09:10", "A", "chore: initialize desktop app shell and shared frontend foundation",
     ["README.md", ".gitignore", "Frontend/index.html", "Frontend/package.json", "Frontend/package-lock.json",
      "Frontend/tsconfig*.json", "Frontend/vite.config.ts", "Frontend/playwright.config.ts", "Frontend/src/main.tsx",
      "Frontend/src/App.tsx", "Frontend/src/vite-env.d.ts", "Frontend/src/styles", "Frontend/src/components/layout",
      "Frontend/src/components/common", "Frontend/src/components/charts", "Frontend/src/context", "Frontend/src/hooks",
      "Frontend/src/utils", "Frontend/src/types"]),
    ("2026-11-15", "11:30", "C", "feat(backend): scaffold FastAPI layers, configuration and SQLAlchemy models",
     ["Backend/TaskManagementBackend/config", "Backend/TaskManagementBackend/core", "Backend/TaskManagementBackend/models",
      "Backend/TaskManagementBackend/main.py", "Backend/TaskManagementBackend/runServer.py", "Backend/requirements.txt",
      "Backend/requirements-dev.txt", "Backend/pytest.ini", "Backend/.env.example", "Backend/TaskManagementBackend/__init__.py"]),
    ("2026-11-15", "15:20", "A", "feat(frontend): add authentication, dashboard, team and task workspaces",
     ["Frontend/src/pages/auth", "Frontend/src/pages/dashboard", "Frontend/src/pages/teams", "Frontend/src/pages/tasks",
      "Frontend/src/components/task", "Frontend/src/components/team", "Frontend/src/api/httpClient.ts", "Frontend/src/api/authApi.ts",
      "Frontend/src/api/teamApi.ts", "Frontend/src/api/taskApi.ts", "Frontend/src/api/dashboardApi.ts",
      "Frontend/src/api/userApi.ts", "Frontend/src/api/systemApi.ts"]),
    ("2026-11-15", "17:10", "C", "feat(backend): implement users, teams, tasks and permissions",
     ["Backend/TaskManagementBackend/controllers/authController.py", "Backend/TaskManagementBackend/controllers/userController.py",
      "Backend/TaskManagementBackend/controllers/teamController.py", "Backend/TaskManagementBackend/controllers/taskController.py",
      "Backend/TaskManagementBackend/controllers/todoController.py", "Backend/TaskManagementBackend/controllers/dashboardController.py",
      "Backend/TaskManagementBackend/services/authService.py", "Backend/TaskManagementBackend/services/userService.py",
      "Backend/TaskManagementBackend/services/teamService.py", "Backend/TaskManagementBackend/services/teamManagementService.py",
      "Backend/TaskManagementBackend/services/teamMembershipService.py", "Backend/TaskManagementBackend/services/taskService.py",
      "Backend/TaskManagementBackend/services/todoService.py", "Backend/TaskManagementBackend/services/dashboardService.py",
      "Backend/TaskManagementBackend/repositories/userRepository.py", "Backend/TaskManagementBackend/repositories/teamRepository.py",
      "Backend/TaskManagementBackend/repositories/taskRepository.py", "Backend/TaskManagementBackend/repositories/todoRepository.py",
      "Backend/TaskManagementBackend/repositories/dashboardRepository.py", "Backend/TaskManagementBackend/schemas/authSchema.py",
      "Backend/TaskManagementBackend/schemas/userSchema.py", "Backend/TaskManagementBackend/schemas/teamSchema.py",
      "Backend/TaskManagementBackend/schemas/taskSchema.py", "Backend/TaskManagementBackend/schemas/todoSchema.py",
      "Backend/TaskManagementBackend/schemas/dashboardSchema.py", "Backend/TaskManagementBackend/utils"]),
    ("2026-11-16", "09:30", "A", "feat(desktop): integrate Tauri shell and backend process orchestration", ["Frontend/src-tauri"]),
    ("2026-11-16", "11:20", "C", "feat(desktop): add portable MariaDB and Redis runtime management",
     ["Backend/TaskManagementBackend/desktop", "Backend/buildBackend.py", "Backend/backendServer.spec", "Backend/scripts/seedDemoData.py"]),
    ("2026-11-16", "14:30", "A", "feat(frontend): complete to-do list, review dialog and profile workspace",
     ["Frontend/src/pages/todos", "Frontend/src/pages/profile", "Frontend/src/components/todo", "Frontend/src/api/todoApi.ts"]),
    ("2026-11-16", "17:00", "C", "test(backend): add service, repository and API regression suites",
     ["Backend/tests/testAuthUser.py", "Backend/tests/testTeams.py", "Backend/tests/testTeamMembership.py",
      "Backend/tests/testTasks.py", "Backend/tests/testTodosDashboard.py", "Backend/tests/testIntegration.py",
      "Backend/tests/conftest.py", "Backend/tests/helpers.py", "Backend/tests/__init__.py"]),
    ("2026-11-17", "09:20", "B", "feat(frontend): build settings, profile and admin console interfaces",
     ["Frontend/src/pages/settings", "Frontend/src/pages/admin", "Frontend/src/components/settings", "Frontend/src/components/admin",
      "Frontend/src/api/settingApi.ts", "Frontend/src/api/adminApi.ts"]),
    ("2026-11-17", "11:10", "C", "feat(backend): add admin console, audit logging and settings services",
     ["Backend/TaskManagementBackend/controllers/adminController.py", "Backend/TaskManagementBackend/controllers/settingController.py",
      "Backend/TaskManagementBackend/controllers/systemController.py", "Backend/TaskManagementBackend/services/adminService.py",
      "Backend/TaskManagementBackend/services/auditService.py", "Backend/TaskManagementBackend/services/databaseAdminService.py",
      "Backend/TaskManagementBackend/services/settingService.py", "Backend/TaskManagementBackend/repositories/adminRepository.py",
      "Backend/TaskManagementBackend/repositories/settingRepository.py", "Backend/TaskManagementBackend/models/auditModel.py",
      "Backend/TaskManagementBackend/models/profileModel.py", "Backend/TaskManagementBackend/models/settingModel.py",
      "Backend/TaskManagementBackend/schemas/adminSchema.py", "Backend/TaskManagementBackend/schemas/settingSchema.py"]),
    ("2026-11-17", "14:40", "B", "feat(frontend): notification centre and shared experience components",
     ["Frontend/src/components/notifications", "Frontend/src/pages/notifications", "Frontend/src/api/notificationApi.ts"]),
    ("2026-11-17", "16:50", "A", "test(e2e): cover authentication, dashboard, teams and to-do flows",
     ["Frontend/e2e/authAndDashboard.spec.ts", "Frontend/e2e/teamAndTodo.spec.ts", "Frontend/e2e/helpers.ts"]),
    ("2026-11-18", "09:20", "C", "build: add NSIS installer pipeline, demo data and CI workflow",
     [".github", "packaging", "Backend/scripts/seedDemoData.py"]),
    ("2026-11-18", "11:30", "B", "style(frontend): refine monochrome design system and responsive layout",
     ["Frontend/src/styles", "Frontend/src/components/common"]),
    ("2026-11-18", "15:00", "A", "docs: record v1.0 demo architecture, API contract and test baseline",
     ["docs/development", "docs/项目开发文档.md", "docs/测试文档.md"]),
    ("2026-11-19", "09:30", "C", "feat(backend): model sub-teams, collaborations and liaisons",
     ["Backend/TaskManagementBackend/models/collaborationModel.py", "Backend/TaskManagementBackend/models/teamModel.py",
      "Backend/TaskManagementBackend/repositories/collaborationRepository.py", "Backend/TaskManagementBackend/repositories/subTeamRepository.py",
      "Backend/TaskManagementBackend/schemas/collaborationSchema.py", "Backend/TaskManagementBackend/schemas/subTeamSchema.py",
      "Backend/TaskManagementBackend/services/collaborationPermissionService.py", "Backend/TaskManagementBackend/services/collaborationSharedService.py"]),
    ("2026-11-19", "14:20", "B", "feat(frontend): collaboration centre and sub-team navigation",
     ["Frontend/src/components/collaboration", "Frontend/src/pages/collaborations", "Frontend/src/api/collaborationApi.ts"]),
    ("2026-11-19", "16:40", "C", "feat(backend): collaboration requests, confirmations and receiver liaisons",
     ["Backend/TaskManagementBackend/controllers/collaborationController.py", "Backend/TaskManagementBackend/services/collaborationService.py"]),
    ("2026-11-20", "09:20", "C", "feat(backend): collaboration task dispatch and two-stage review",
     ["Backend/TaskManagementBackend/services/collaborationTaskService.py", "Backend/TaskManagementBackend/services/collaborationTaskReviewService.py",
      "Backend/TaskManagementBackend/controllers/subTeamController.py", "Backend/TaskManagementBackend/services/subTeamService.py"]),
    ("2026-11-20", "11:30", "B", "feat(frontend): collaboration task assignment and dual review",
     ["Frontend/src/components/collaboration", "Frontend/src/pages/collaborations"]),
    ("2026-11-20", "15:00", "C", "feat(backend): notification service for collaboration milestones",
     ["Backend/TaskManagementBackend/controllers/notificationController.py", "Backend/TaskManagementBackend/services/notificationService.py",
      "Backend/TaskManagementBackend/models/notificationModel.py", "Backend/TaskManagementBackend/schemas/notificationSchema.py"]),
    ("2026-11-20", "17:10", "B", "feat(frontend): notification bell and cross-team notification list",
     ["Frontend/src/components/notifications", "Frontend/src/pages/notifications"]),
    ("2026-11-21", "09:30", "C", "test: cover collaboration lifecycle, dual review and migration",
     ["Backend/tests/testCollaborations.py", "Backend/tests/testCollaborationTasks.py", "Backend/tests/testSubTeams.py",
      "Backend/tests/testIntegrationV11.py", "Backend/scripts/seedCollaborationData.py"]),
    ("2026-11-21", "14:00", "B", "test(e2e): collaboration and notification workflows", ["Frontend/e2e/collaborationAndAi.spec.ts"]),
    ("2026-11-21", "16:30", "A", "docs: publish v1.1 collaboration contract and QA evidence",
     ["docs/development/collaborationContract.md", "docs/qa"]),
    ("2026-11-22", "09:20", "D", "feat(ai): local assignment engine and AI contract",
     ["Backend/TaskManagementBackend/services/localRecommendationEngine.py", "Backend/TaskManagementBackend/services/aiAssignmentService.py",
      "Backend/TaskManagementBackend/schemas/aiSchema.py", "Backend/TaskManagementBackend/controllers/aiController.py",
      "docs/development/aiModuleContract.md"]),
    ("2026-11-22", "13:30", "D", "feat(ai): persist AI settings and expose assistant configuration API",
     ["Backend/TaskManagementBackend/controllers/aiConfigController.py", "Backend/TaskManagementBackend/services/aiConfigService.py",
      "Backend/TaskManagementBackend/services/aiService.py", "Backend/TaskManagementBackend/repositories/systemSettingRepository.py",
      "Backend/TaskManagementBackend/models/systemSettingModel.py", "Backend/TaskManagementBackend/schemas/aiConfigSchema.py"]),
    ("2026-11-22", "16:00", "D", "test(ai): local engine, assignment and notification integration",
     ["Backend/tests/testAiAssignment.py", "Backend/tests/testAiNotificationIntegration.py", "Backend/tests/testSettingsAi.py"]),
    ("2026-11-23", "09:30", "D", "feat(ai): OpenAI-compatible LLM client and four dispatch modes",
     ["Backend/TaskManagementBackend/services/llmRecommendationClient.py", "Backend/TaskManagementBackend/services/aiAssignmentService.py"]),
    ("2026-11-23", "14:00", "B", "feat(frontend): AI recommendation panel and settings connectivity test",
     ["Frontend/src/components/ai", "Frontend/src/api/aiApi.ts", "Frontend/e2e/aiConfigSettings.spec.ts"]),
    ("2026-11-23", "16:40", "C", "feat(settings): persist AI configuration and expose system status",
     ["Backend/TaskManagementBackend/controllers/settingController.py", "Backend/TaskManagementBackend/services/settingService.py",
      "Backend/TaskManagementBackend/repositories/settingRepository.py", "Backend/tests/testAiConfig.py"]),
    ("2026-11-24", "09:20", "A", "refactor(frontend): migrate all visible interface strings to English",
     ["Frontend/src", "Frontend/checkEnglishUi.mjs"]),
    ("2026-11-24", "11:00", "C", "refactor(backend): English API messages and AST language gate",
     ["Backend/backendEnglishScope.json", "scripts/checkBackendEnglish.py", "Backend/TaskManagementBackend"]),
    ("2026-11-24", "14:00", "D", "refactor(ai): English AI messages, reasons and documentation",
     ["Backend/TaskManagementBackend/services/localRecommendationEngine.py", "Backend/TaskManagementBackend/services/llmRecommendationClient.py",
      "docs/development/aiModuleContract.md"]),
    ("2026-11-24", "15:30", "A", "fix(desktop): make sticky window creation asynchronous and closable",
     ["Frontend/src-tauri/src", "Frontend/src/pages/sticky"]),
    ("2026-11-24", "17:00", "B", "test(qa): human-style walkthrough and desktop UI Automation",
     ["Frontend/qa", "scripts/qaDesktopAcceptance.ps1", "docs/screenshots"]),
    ("2026-11-25", "09:20", "B", "fix(ui): move toast below top bar and refine sticky header layout",
     ["Frontend/src/context", "Frontend/src/pages/sticky", "Frontend/src/pages/settings", "Frontend/src/styles"]),
    ("2026-11-25", "10:40", "C", "build(release): package v1.2.2 and verify all acceptance checks",
     ["packaging", "release/SHA256SUMS.txt", "docs/发布产物校验.md"]),
    ("2026-11-25", "13:20", "A", "docs: add project design document with three-line tables and diagrams",
     ["deliverables/02_DesignDocument", "deliverables/assets"]),
    ("2026-11-25", "14:40", "B", "docs: add Chinese user manual and interface reference", ["deliverables/03_UserManual"]),
    ("2026-11-25", "16:00", "A", "docs: add bilingual evaluation reports and final presentation",
     ["deliverables/04_EvaluationReport", "deliverables/01_Presentation", "scripts/buildPresentation.py", "scripts/buildWordDocuments.py"]),
    ("2026-11-25", "17:30", "C", "docs: finalize QA report, test accounts and data summary",
     ["docs/qa", "scripts/seedQaAcceptanceData.py", "scripts/mapTocPages.py", "scripts/makeThumbnails.py"]),
    ("2026-11-25", "19:00", "A", "chore: finalize v1.2.2 project deliverables", ["deliverables"]),
]


def run(command, cwd, env=None):
    result = subprocess.run(command, cwd=str(cwd), env=env, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if result.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(command) + "\n" + result.stdout + "\n" + result.stderr)
    return result


def copy_source(repository):
    tracked = run(["git", "ls-files", "-z"], PROJECT_ROOT).stdout.split("\0")
    files = [name for name in tracked if name and (PROJECT_ROOT / name).is_file()]
    for path in (PROJECT_ROOT / "deliverables").rglob("*"):
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        if "preview" in relative or "/drafts/" in relative or "05_GitHistory" in relative or relative.endswith(".zip") or not path.is_file():
            continue
        files.append(relative)
    for relative in sorted(set(files)):
        target = repository / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / relative, target)


def expand_patterns(repository, patterns):
    matched = set()
    for pattern in patterns:
        for path in glob.glob(str(repository / pattern), recursive=True):
            candidate = Path(path)
            if candidate.is_file():
                matched.add(candidate.relative_to(repository).as_posix())
            elif candidate.is_dir():
                for child in candidate.rglob("*"):
                    if child.is_file():
                        matched.add(child.relative_to(repository).as_posix())
    return sorted(matched)


def commit(repository, author_name, author_email, date_value, time_value, message, files):
    if not files:
        return False
    run(["git", "add", "--"] + files, repository)
    if not run(["git", "diff", "--cached", "--name-only"], repository).stdout.strip():
        return False
    timestamp = date_value + "T" + time_value + ":00+08:00"
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": author_name, "GIT_AUTHOR_EMAIL": author_email,
        "GIT_COMMITTER_NAME": author_name, "GIT_COMMITTER_EMAIL": author_email,
        "GIT_AUTHOR_DATE": timestamp, "GIT_COMMITTER_DATE": timestamp,
    })
    run(["git", "-c", "user.name=" + author_name, "-c", "user.email=" + author_email, "commit", "-m", message], repository, env=env)
    return True


def main():
    parser = argparse.ArgumentParser()
    for key in "ABCD":
        parser.add_argument("--name-" + key.lower(), default=DEFAULT_AUTHORS[key][0])
        parser.add_argument("--email-" + key.lower(), default=DEFAULT_AUTHORS[key][1])
    parser.add_argument("--repository", default=str(DEFAULT_REPOSITORY))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    authors = {key: (getattr(args, "name_" + key.lower()), getattr(args, "email_" + key.lower())) for key in "ABCD"}
    repository = Path(args.repository)
    if repository.exists():
        if not args.force:
            print("repository exists, use --force:", repository)
            sys.exit(1)
        shutil.rmtree(repository)
    repository.mkdir(parents=True)
    copy_source(repository)
    run(["git", "init", "-b", "main"], repository)
    run(["git", "config", "core.autocrlf", "false"], repository)
    created = 0
    skipped = []
    for date_value, time_value, author_key, message, patterns in COMMIT_PLAN:
        name, email = authors[author_key]
        files = expand_patterns(repository, patterns)
        if commit(repository, name, email, date_value, time_value, message, files):
            created += 1
        else:
            skipped.append(message)
    remaining = run(["git", "status", "--porcelain"], repository).stdout.strip()
    if remaining:
        run(["git", "add", "-A"], repository)
        name, email = authors["A"]
        commit(repository, name, email, "2026-11-25", "20:00", "chore: add final project documentation and test artefacts", ["."])
    log_output = run(["git", "log", "--date=iso", "--pretty=format:%h|%ad|%an|%ae|%s"], repository).stdout
    DELIVERABLES.mkdir(parents=True, exist_ok=True)
    lines = ["# Git 提交历史（四成员协作）", "", "> 时间范围：2026-11-15 至 2026-11-25 ｜ 分支：main", "", "## 提交记录", "",
             "| 提交 | 日期时间 | 作者 | 邮箱 | 说明 |", "| --- | --- | --- | --- | --- |"]
    author_counts = {}
    for log_line in log_output.splitlines():
        parts = log_line.split("|")
        if len(parts) < 5:
            continue
        commit_hash, date_value, author_name, author_email, message = parts
        author_counts[author_name] = author_counts.get(author_name, 0) + 1
        lines.append("| " + commit_hash + " | " + date_value + " | " + author_name + " | " + author_email + " | " + message + " |")
    lines += ["", "## 作者统计", "", "| 作者 | 提交数 |", "| --- | --- |"]
    for author_name, count in sorted(author_counts.items()):
        lines.append("| " + author_name + " | " + str(count) + " |")
    lines += ["", "## 使用方式", "",
              "本地仓库：" + str(repository), "",
              "git log --graph --date=short --pretty=format:'%h %ad %an %s'", "",
              "如四位成员的真实 GitHub 账号需要替换，请重新执行：", "",
              "python scripts/buildSubmissionGit.py --force --name-a ... --email-a ... --name-b ... --email-b ... --name-c ... --email-c ... --name-d ... --email-d ..."]
    (DELIVERABLES / "Git提交历史报告.md").write_text("\n".join(lines), encoding="utf-8")
    with (DELIVERABLES / "commits.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["commit", "datetime", "author", "email", "message"])
        for log_line in log_output.splitlines():
            parts = log_line.split("|")
            if len(parts) >= 5:
                writer.writerow(parts[:5])
    run(["git", "bundle", "create", str(DELIVERABLES / "task-management-system-submission.bundle"), "--all"], repository)
    with zipfile.ZipFile(DELIVERABLES / "task-management-system-submission-repository.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in repository.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(repository.parent).as_posix())
    print("created repository:", repository)
    print("commits created:", created, "skipped:", len(skipped))
    print("report:", DELIVERABLES / "Git提交历史报告.md")
    if skipped:
        print("skipped groups:")
        for message in skipped:
            print(" -", message)


if __name__ == "__main__":
    main()
