readme.xsw.txt
================================================================================
Task 3 - Project Plan: Frontend 2 slice
Owner      : Xu Shiwei
Team       : 4 people (Sun Xinjian, Xu Shiwei, Ye Tao, Wu Zeye)
Stack      : HTML + CSS + TypeScript + Bootstrap (front end)
             Python + FastAPI + MySQL (back end, front/back separated)
Status     : planning - page skeleton not started
================================================================================


0. PROJECT IN ONE PARAGRAPH
--------------------------------------------------------------------------------
We are building a small task-management system for a project team. Users register
and log in, publish a task with a required skill tag, the system assigns the task
to a member whose personal capability tags match, and each member sees the tasks
they own, submits them and marks them done. Assignment can be automatic (tag plus
current workload) or manual (a human decides). My part is the front end of the
task side: the task management pages and the overall task list of the whole
project.


1. MY ROLE AND SCOPE
--------------------------------------------------------------------------------
Role in 3.1   : Frontend 2
Own           : - task management pages (create / read / update / delete a task)
                - the overall task list showing every task in the project
Not mine      : - login, registration, page routing, personal capability page,
                  auto-assign page (these are Sun Xinjian, Frontend 1)
                - FastAPI endpoints, database tables (Ye Tao)
                - auto-assignment algorithm, attribute storage (Wu Zeye)

Rule of thumb: I never write server code. If an endpoint I need does not exist,
I write down the request/response I expect and hand it to Ye Tao or Wu Zeye
instead of inventing a local mock that later has to be thrown away.


2. WHAT I MUST DELIVER
--------------------------------------------------------------------------------
2.1 Task management page (single task)
    Required fields on the create/edit form:
      - title                 text, required, max 80 characters
      - description           textarea, optional
      - required skill tag    single select from the shared tag dictionary
                              (java / c++ / c / python / ... - never free text)
      - priority              low / normal / high
      - due date              date picker, optional
      - status                open / assigned / in progress / submitted / done
    Actions:
      - create a task
      - edit a task (all fields except the creator and created_at)
      - delete a task (with a confirmation dialog, no silent delete)
      - submit a task and mark it done
    Validation shown inline, not as an alert box:
      - empty title, title too long, no tag selected, due date in the past

2.2 Overall task list (all tasks in the project)
    One table, no pagination on day one, but built so pagination can be added
    without rewriting the component.
    Columns: title | tag | status | assignee | priority | due date | actions
    Must support:
      - filter by status, by tag, by assignee, and a free-text search on title
      - sort by due date and by created time, ascending and descending
      - row actions: view, edit, delete, manual assign
      - a visible counter: "showing X of Y tasks"
    Status must be readable without hovering: colour badge plus the text label,
    because colour-blind readers will otherwise lose the state.

2.3 States every one of my pages must handle
    - empty      : "no tasks yet" plus the button that creates the first one
    - loading    : skeleton rows, not a spinning gif
    - error      : what failed and a retry button
    - partial    : request succeeded but the list is filtered down to nothing,
                   which is a different message from "no tasks exist"


3. API CONTRACT I DEPEND ON (proposal - to be confirmed with Ye Tao)
--------------------------------------------------------------------------------
These are the endpoints my pages need. I write this table first so back end work
and my work can run in parallel; a mock may be used for one week only and is
deleted as soon as the real endpoint exists.

  Method  Path                        Purpose
  ------  --------------------------  ----------------------------------------
  GET     /api/tags                   tag dictionary for the dropdown
  GET     /api/tasks                  all tasks, with filters as query params
  GET     /api/tasks/{id}             one task
  POST    /api/tasks                  create
  PATCH   /api/tasks/{id}             edit
  DELETE  /api/tasks/{id}             delete
  POST    /api/tasks/{id}/claim       receive a task (assign to me)
  POST    /api/tasks/{id}/submit      submit work
  POST    /api/assign/auto            run automatic assignment
  GET     /api/users/{id}/tasks       tasks of one person

  Task object:
    {
      "id": 12,
      "title": "Build the task list page",
      "description": "",
      "tag": "typescript",            // from the dictionary, lowercase
      "priority": "high",             // low | normal | high
      "status": "assigned",           // open | assigned | in_progress
                                      // | submitted | done
      "assignee_id": 3,
      "created_by": 1,
      "due_date": "2026-11-02",
      "created_at": "2026-10-20T09:15:00"
    }

  List responses wrap items and a total:
    { "items": [ ... ], "total": 42 }

  Errors always return { "detail": "message" } with a 4xx/5xx status, and my
  pages display detail verbatim instead of a generic "something went wrong".


4. ITERATION PLAN FOR MY PART
--------------------------------------------------------------------------------
Iteration 1 - pages exist and talk to the back end
  [ ] Task list page rendered from a static JSON file (skeleton first)
  [ ] Task form built and validated on the client
  [ ] Filters, sorting and the counter wired up
  [ ] Login state read from Sun Xinjian's auth page; unauthenticated users are
      redirected to login instead of seeing an empty table
  [ ] Replace the static JSON with GET /api/tasks
  [ ] Create, edit and delete confirmed against the real endpoints
  [ ] One full round-trip tested: form -> API -> list refresh

Iteration 2 - assignment and personal routing
  [ ] [Auto-assign] button calls POST /api/assign/auto, then the list refreshes
  [ ] Show the assignee on each row immediately after assignment, without a
      manual reload
  [ ] Personal task routing: "my tasks" view uses the same table component with
      assignee_id = me (Sun Xinjian owns the route, I own the list behaviour)
  [ ] Guard against the known bugs:
      [ ] two people with the same tag - the row shows exactly one assignee
      [ ] a person at the task cap - the assign button explains why it stopped
      [ ] a task with no matching tag - stays "open" and says so in the list


5. ACCEPTANCE CRITERIA I AM ACCOUNTABLE FOR
--------------------------------------------------------------------------------
From 3.3, the ones that pass or fail on my pages:
  [ ] Able to publish tasks/work
  [ ] Able to display work completion status
  [ ] Able to manually assign work
  [ ] Able to submit work                      (submission UI on the task page)
  [ ] Able to receive work                     (claim action on the list)
  [ ] Able to delete and modify tasks          (edit and delete actions)
  [ ] Able to be deployed normally             (my pages load with no console
                                                errors after deployment)
  Not mine but I must not break: log in, register, automatic assignment,
  personal tags.


6. DEPENDENCIES AND HAND-OFFS
--------------------------------------------------------------------------------
Sun Xinjian : login/registration, page routing and the capability page. I need
              the route names and the current-user object (id, name, tags) from
              him before iteration 1 ends.
Ye Tao      : FastAPI skeleton and the task endpoints. Needs my contract table
              (section 3) on day 1 so he can stub the routes.
Wu Zeye     : assignment algorithm and attribute storage. Needs to tell me the
              response shape of POST /api/assign/auto (who got what, and why a
              task was not assigned) so the list can explain it.
Me          : the two pages, the shared table component, and the error states.


7. RISKS FROM MY SIDE, AND WHAT I DO ABOUT THEM
--------------------------------------------------------------------------------
Tag mismatch (upper/lower case, spelling)
  -> the tag field is a dropdown fed by GET /api/tags; no free-text input at all
Task piling on one person
  -> the list shows the current task count per assignee so the cap is visible
     before the auto-assign button is pressed
Same-skill duplication (two people, same tag)
  -> after assignment I re-fetch the row instead of patching it locally, so the
     list always shows server truth
Scope creep into back end work
  -> any endpoint I need is written in section 3 and handed over; I do not add
     hidden client-side business rules


8. DEFINITION OF DONE (my part)
--------------------------------------------------------------------------------
  [ ] Both pages work against the real API, no mock data left in the code
  [ ] Every state in 2.3 is implemented and can be triggered on purpose
  [ ] Console has no errors and no failed network requests on a clean load
  [ ] The four list behaviours (filter / sort / search / counter) survive an
      empty result without breaking the layout
  [ ] A teammate can use the pages without me explaining them
  [ ] Files committed on a branch, one reviewer (not me) approves the PR


9. FILES I EXPECT TO OWN IN THE REPO
--------------------------------------------------------------------------------
  frontend/src/pages/tasks/TaskList.ts        overall task list + filters
  frontend/src/pages/tasks/TaskForm.ts        create / edit form + validation
  frontend/src/components/TaskTable.ts        shared table, used by both views
  frontend/src/api/tasks.ts                   the calls in section 3
  frontend/src/types/task.ts                  Task, TaskStatus, Tag types
  docs/api-contract.xsw.md                    section 3, kept up to date

(Names are a proposal; align with Sun Xinjian's folder layout in iteration 1.)


10. OPEN QUESTIONS
--------------------------------------------------------------------------------
  1. Is the overall task list visible to everyone, or filtered by role? Section
     3.3 says "all current work (for the entire project)", but the acceptance
     criteria mention permissions. Needs an answer before iteration 1 ends.
  2. Does "receive work" mean the assignee accepts an auto-assigned task, or a
     member claims an unassigned one? Both need a button; only one may be built.
  3. Is deletion a hard delete or a status change? It affects whether the list
     counter and the acceptance test "able to delete" still pass after a reload.
  4. Who owns the tag dictionary - Wu Zeye (storage) or me (UI)? The list must
     agree with the dropdown or filters will return nothing.


--------------------------------------------------------------------------------
Written by Xu Shiwei. Keep this file updated; it is the record of what I agreed
to build, and it is what I will check against before the demo.
