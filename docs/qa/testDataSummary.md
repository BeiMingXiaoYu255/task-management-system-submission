# QA Acceptance Test Data Summary (v1.2.2)

> Generated at 2026-11-25T22:23:56; base API: http://127.0.0.1:8765
> Regenerate with: python scripts/seedQaAcceptanceData.py (idempotent).
> LAN access: (not configured)

## 1. Accounts and roles

- QA accounts: 10; plus built-in superAdmin.
- globalAdmin: qaGlobalAdmin; disabled user: qaDisabledUser; team admins: qaTeamAdminA (QA Alpha Team), qaTeamAdminB (QA Beta Team / QA Gamma Pending Team creator); sub-admin: qaSubAdminA.
- See testAccounts.md and testAccounts.json for the full account list.

## 2. Teams and member levels

| Team ID | Team Name | Certification | Join Method | Members |
| --- | --- | --- | --- | --- |
| 1 | QA Alpha Team | Certified | approval | 4 |
| 2 | QA Beta Team | Certified | inviteOnly | 3 |
| 3 | QA Gamma Pending Team | Pending | approval | 1 |

- QA Alpha Team has the custom level QA Lead (levelOrder=4, canCreateTask=true) used by qaSubAdminA.
- QA Alpha Team uses approval join and keeps one pending join request; QA Beta Team uses invite-code join.

## 3. Tasks (15)

| Team | Title | Status | Priority | Assignment | Acceptance | Assignees |
| --- | --- | --- | --- | --- | --- | --- |
| QA Alpha Team | QA Alpha AI Auto-assigned Task | inProgress | high | specific | mandatory | qaMemberA1 |
| QA Alpha Team | QA Alpha Level Range Optional Task | published | high | levelRange | optional | qaMemberA1, qaMemberA2 |
| QA Alpha Team | QA Alpha Cancelled Task | cancelled | high | specific | mandatory | qaMemberA2 |
| QA Alpha Team | QA Alpha Pending Review Task | pendingReview | medium | specific | mandatory | qaMemberA2 |
| QA Alpha Team | QA Alpha Overdue Task | inProgress | urgent | specific | mandatory | qaMemberA1 |
| QA Alpha Team | QA Alpha In Progress Sub-team Task | inProgress | high | specific | mandatory | qaMemberA2 |
| QA Alpha Team | QA Alpha Optional Published Task | published | medium | specific | optional | qaMemberA1 |
| QA Alpha Team | QA Alpha Archived Task | archived | low | specific | mandatory | qaMemberA1 |
| QA Beta Team | QA Beta Manual Assign Task | inProgress | low | specific | mandatory | qaMemberB1 |
| QA Beta Team | QA Beta Level Range Task | inProgress | medium | levelRange | mandatory | qaMemberB1, qaMemberB2 |
| QA Beta Team | QA Beta Cancelled Task | cancelled | urgent | specific | mandatory | qaMemberB1 |
| QA Beta Team | QA Beta Pending Review Task | pendingReview | low | specific | mandatory | qaMemberB1 |
| QA Beta Team | QA Beta In Progress Task | inProgress | high | specific | mandatory | qaMemberB2 |
| QA Beta Team | QA Beta Optional Published Task | published | medium | specific | optional | qaMemberB1 |
| QA Beta Team | QA Beta Archived Task | archived | medium | specific | mandatory | qaMemberB2 |

- Statuses: published / inProgress / pendingReview / archived / cancelled.
- Priorities: low / medium / high / urgent; specific member and level-range assignment; mandatory and optional acceptance.
- The overdue task due date was moved into the past through the admin single-statement DML API.
- AI auto-assigned task: 8 (QA Alpha AI Auto-assigned Task), assignmentSource=ai.
- Manual assignment task: 15 (AI match failure, then manual assignee).

## 4. To-dos (/todos/stats per user)

| User | total | pendingAcceptance | inProgress | pendingReview | archived | overdue |
| --- | --- | --- | --- | --- | --- | --- |
| qaMemberA1 | 4 | 2 | 2 | 0 | 1 | 1 |
| qaMemberA2 | 3 | 1 | 1 | 1 | 0 | 0 |
| qaMemberB1 | 6 | 1 | 3 | 2 | 0 | 0 |
| qaMemberB2 | 2 | 0 | 2 | 0 | 1 | 0 |

## 5. Sub-teams

| Sub-team ID | Name | Team | Leader | Members |
| --- | --- | --- | --- | --- |
| 1 | Frontend Squad | QA Alpha Team | qaMemberA1 | 2 |
| 2 | Backend Squad | QA Alpha Team | qaSubAdminA | 1 |

## 6. Collaborations and collaboration tasks

| Collaboration ID | Status | Initiator Unit | Receiver Unit |
| --- | --- | --- | --- |
| 1 | active | QA Alpha Team | QA Beta Team |
| 2 | pending | QA Alpha Team - Frontend Squad | QA Beta Team |

| Collaboration Task | Phase | Status |
| --- | --- | --- |
| QA Collaboration Target Review Task | targetReview | pendingReview |
| QA Collaboration Executing Task | executing | inProgress |
| QA Collaboration Pending Confirmation Task | pendingConfirmation | published |

## 7. Notifications

- Triggered by collaboration request/confirmation, collaboration task confirm/submit, task review results, AI auto-assignment / match reminder / assignment failure and manual assignment.
- qaMemberA2 and qaMemberB2 each have one notification marked as read; the rest stay unread.

| User | Unread notifications |
| --- | --- |
| qaMemberA1 | 2 |
| qaMemberA2 | 2 |
| qaMemberB1 | 3 |
| qaMemberB2 | 4 |
| qaTeamAdminA | 3 |
| qaTeamAdminB | 3 |

## 8. AI configuration

- dispatchMode=LOCAL_ONLY (LOCAL_ONLY, local rule engine).
- matchThreshold=20; workloadPenalty=2.
- LLM configured=False; /ai/status provider=hybrid.

## 9. Skipped items / known limitations

None.

## 10. Idempotency

- The script looks up accounts by username, teams by name and tasks by title, so re-running it reuses existing data.
- Re-running also repairs missing memberships, roles/levels, task states and collaborations.
- If the application data is reset, re-run the script to rebuild the whole QA dataset.
