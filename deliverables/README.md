# 任务管理系统 项目交付物

> 项目版本：v1.2.2 ｜ 交付日期：2026-11-25 ｜ 团队：成员 A / B / C / D

本目录包含课程/项目提交所需的全部文档、演示文稿、图表素材与 Git 协作记录。所有文件均已用 LibreOffice 渲染检查，并提供 PDF 便于直接预览；Office 源文件可继续编辑。

## 一、交付文件

| 目录 | 文件 | 说明 |
| --- | --- | --- |
| [01_Presentation](01_Presentation/) | [TaskManagementSystem_Project_Presentation.pptx](01_Presentation/TaskManagementSystem_Project_Presentation.pptx) | 英文演示文稿，18 页 16:9；含设计背景、技术栈、系统架构、核心工作流、Time Boxing、流程改进证据、A/B/C/D 贡献与局限 |
| | [TaskManagementSystem_Project_Presentation.pdf](01_Presentation/TaskManagementSystem_Project_Presentation.pdf) | PPT 渲染版 |
| [02_DesignDocument](02_DesignDocument/) | [项目设计文档.docx](02_DesignDocument/项目设计文档.docx) | 中文，黑白二色，三线表，LaTeX 式章节/图表编号；28 页 |
| | [项目设计文档.pdf](02_DesignDocument/项目设计文档.pdf) | 设计文档渲染版 |
| [03_UserManual](03_UserManual/) | [任务管理系统_项目说明书.docx](03_UserManual/任务管理系统_项目说明书.docx) | 中文用户手册，15 章 + 附录；47 页，含界面真实截图 |
| | [任务管理系统_项目说明书.pdf](03_UserManual/任务管理系统_项目说明书.pdf) | 用户手册渲染版 |
| [04_EvaluationReport](04_EvaluationReport/) | [ProjectEvaluationReport_EN.docx](04_EvaluationReport/ProjectEvaluationReport_EN.docx) | 英文评估报告，正文满足 ≤2500 词（不含参考文献），APA7 引用 |
| | [项目评估报告_中文版.docx](04_EvaluationReport/项目评估报告_中文版.docx) | 中文评估报告，结构与英文版一致 |
| | [ProjectEvaluationReport_EN.pdf](04_EvaluationReport/ProjectEvaluationReport_EN.pdf) / [项目评估报告_中文版.pdf](04_EvaluationReport/项目评估报告_中文版.pdf) | 渲染版 |
| [05_GitHistory](05_GitHistory/) | [Git提交历史报告.md](05_GitHistory/Git提交历史报告.md) | 四成员协作提交记录（共 38 个提交，2026-11-15 至 11-25），作者统计与替换账号说明 |
| | [commits.csv](05_GitHistory/commits.csv) | 提交明细 CSV |
| | [task-management-system-submission.bundle](05_GitHistory/task-management-system-submission.bundle) / [task-management-system-submission-repository.zip](05_GitHistory/task-management-system-submission-repository.zip) | 可直接克隆/解压查看的完整提交历史 |
| [06_QA](06_QA/) | [测试账号.md](06_QA/测试账号.md) / [测试数据摘要.md](06_QA/测试数据摘要.md) | v1.2.2 实机 QA 使用的账号与数据集（安装版当前已写入该数据集） |
| [assets](assets/) | `architecture.png`、`module-map.png`、`task-lifecycle.png`、`collaboration-workflow.png`、`ai-assignment.png`、`timeboxing.png`、`process-improvement.png`、`runtime-packaging.png`、`ui-*.png` / `thumb-*.png` | 文档与 PPT 使用的架构图、模块图、流程图、时间线、质量证据图与界面截图 |

## 二、文档与内容对应

### 1. 演示文稿（英文）
- **Design background**：小团队任务碎片化、跨团队无握手、云服务不可用，引出离线桌面 + 局域网目标。
- **Tech stack / Architecture / Module map**：Tauri 2 + React 18 + FastAPI + MariaDB 11.4 + Redis，一张部署架构图和一张模块图。
- **Core workflows**：任务生命周期（发布→接受→提交→审核→归档/驳回）与协作双审核（双方确认对接人→协作任务→接收方审核→发起方审核→归档）。
- **Process improvement evidence**：验证覆盖增长（后端 63→136、E2E 12→21、真人 UI 检查 0→62、安装包检查 16→76）、缺陷闭环、验收证据。
- **Development process**：Time Boxing 四个时间盒（11/15–18、11/19–21、11/22–23、11/24–25）。
- **Team contributions**：A 前端基础与任务域、B 协作与体验域、C 后端与数据库、D AI 模块；配图见第 15–16 页。

### 2. 项目设计文档（中文，黑白，三线表）
- 章节：项目背景与目的 → 技术栈 → 模块设计与系统架构 → 技术实现 → 测试结果 → 开发过程（三个迭代） → 结论与展望 → 参考文献。
- 含 15 张三线表、8 张图表（架构、模块、任务状态机、协作双审核、AI 分配、Time Boxing、质量门禁、运行时打包）。
- 图题在图下、表题在表上，图/表/公式按章编号；页眉页脚与页码齐全。

### 3. 项目说明书（中文）
- 覆盖安装版/便携版/局域网三种形态、登录注册、界面总览、团队与成员级别、任务全流程、待办与便签、协作双审核、AI 配置与自动分配、通知、设置、管理后台、备份升级与常见问题。
- 界面自 v1.2.0 起为英文，正文用“English（中文）”标注。

### 4. 项目评估报告（中英双语）
- 章节：Introduction / Scope and Changes / Iteration Outcomes / Software Quality Results / Process Improvement / Comparative Evaluation / Limitations / Conclusion / References。
- 英文正文满足 ≤2500 词（不含 20 条 APA7 References），中文约 4,200 字；引用覆盖 Tauri、React、FastAPI、SQLAlchemy、Pydantic、Scrum Guide、ISO/IEC 25010、Sommerville、Martin、Cohn、Brooks、Fowler、Nielsen、OWASP 等真实来源。

### 5. Git 协作记录
- 四个成员（Member A/B/C/D 占位身份）在 2026-11-15 至 11-25 之间产生 37 个逻辑提交，覆盖初始化、前端/后端、协作、AI、英文界面、缺陷修复、打包与文档。
- 完整仓库：`C:\Users\q1506\Desktop\SoftwareDevelopment\task-management-system-submission-git`；也可用 bundle/zip 导入。
- **替换真实 GitHub 账号**：拿到四人的姓名与邮箱后执行：
  ```bash
  python scripts/buildSubmissionGit.py --force \\
    --name-a "A 姓名" --email-a a@example.com \\
    --name-b "B 姓名" --email-b b@example.com \\
    --name-c "C 姓名" --email-c c@example.com \\
    --name-d "D 姓名" --email-d d@example.com
  ```
  脚本会重建 `submission-git` 仓库并覆盖 `05_GitHistory` 下的报告与 bundle/zip。

## 三、校验与复现

- 文档渲染：`soffice --headless --convert-to pdf <docx/pptx>`，LibreOffice 24.x；PDF 检查通过。
- 图表生成：`cd Frontend && node qa/generateDiagrams.mjs`；界面截图来自 v1.2.2 真人式 QA 与桌面 UIA 验收（`docs/qa/qaAcceptanceReport.md`）。
- 项目质量数据：后端 pytest 136/136、Playwright E2E 21/21、真人式 QA Web 33/33、桌面 29/29、安装包验收 16/16 + 15/15 + 24/24 + 21/21。
- Word/PPT 生成脚本：`scripts/buildWordDocuments.py`、`scripts/buildPresentation.py`；办公文件均可用 Microsoft Office / LibreOffice 打开编辑。

> 备注：设计文档、评估报告为课程作业文档，测试数据与安装包来自项目 v1.2.2 实机验收；真实 LLM API 连通性未验证（无生产密钥），评估报告“局限性”章节已如实说明。
