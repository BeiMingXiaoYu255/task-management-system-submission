# QA Acceptance Test Accounts (v1.2.2)

> Generated at 2026-11-25T22:23:56; base API: http://127.0.0.1:8765
> All QA accounts share the password Qa@123456.
> LAN access: (not configured)

| Username | Password | Global Role | Team | Team Role / Level | Purpose |
| --- | --- | --- | --- | --- | --- |
| superAdmin | SuperAdmin@123 | superAdmin | - | - | 内置超级用户：可认证团队、设置全局管理员、管理后台数据库只读浏览 |
| qaGlobalAdmin | Qa@123456 | globalAdmin | - | - | 全局管理员：管理后台概览、用户/团队认证、数据库只读浏览、AI 配置 |
| qaTeamAdminA | Qa@123456 | user | QA Alpha Team | admin / Senior Member | QA Alpha Team 团队管理员：发布/修改/取消/审核任务、生成邀请码、管理成员级别 |
| qaTeamAdminB | Qa@123456 | user | QA Beta Team | admin / Senior Member | QA Beta Team 团队管理员 + QA Gamma 待认证团队创建者：协作接收方管理员 |
| qaSubAdminA | Qa@123456 | user | QA Alpha Team | subAdmin / QA Lead | QA Alpha Team 子管理员（自定义级别 QA Lead）：入团审核、邀请码、低级别成员管理 |
| qaMemberA1 | Qa@123456 | user | QA Alpha Team | member / Intermediate Member | QA Alpha Team 普通成员 / Frontend Squad 子负责人：待接受、进行中、已归档、AI 自动分配执行人 |
| qaMemberA2 | Qa@123456 | user | QA Alpha Team | member / Intermediate Member | QA Alpha Team 普通成员：逾期任务、待审核任务执行人；协作发起方对接人 |
| qaMemberB1 | Qa@123456 | user | QA Beta Team | member / Junior Member | QA Beta Team 普通成员（邀请码加入）：待办各状态、协作任务执行人 |
| qaMemberB2 | Qa@123456 | user | QA Beta Team | member / Junior Member | QA Beta Team 普通成员：协作接收方对接人（接收方双审核） |
| qaApplicantAlpha | Qa@123456 | user | - | - | 非成员账号：对 QA Alpha Team 有一条待处理入团申请（用于入团审核测试） |
| qaDisabledUser | Qa@123456 | user | - | - | 已禁用账号：登录返回 ACCOUNT_DISABLED（用于禁用账号与错误提示测试） |

## Login notes

1. Open the application (desktop or browser) and sign in with any account above.
2. superAdmin can open the Admin Console for team certification, global admin management and database browsing.
3. qaGlobalAdmin is a global admin (Admin Console access, no super-admin-only actions).
4. qaTeamAdminA / qaTeamAdminB own certified teams and can publish and review tasks.
5. qaDisabledUser is disabled; signing in must return ACCOUNT_DISABLED.
