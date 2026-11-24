/**
 * 生成项目演示/文档所需的英文示意图（SVG -> PNG，黑白极简风格）。
 * 运行：cd Frontend && node ../scripts/generateProjectDiagrams.mjs
 */
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from '@playwright/test'

const projectRoot = path.resolve(process.cwd(), '..')
const outputDirectory = path.join(projectRoot, 'deliverables', 'assets')
fs.mkdirSync(outputDirectory, { recursive: true })

const FONT = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
const MONO = "'Cascadia Mono', Consolas, monospace"

function escapeXml(text) {
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function text(x, y, value, options = {}) {
  const { size = 20, weight = 400, anchor = 'start', fill = '#111', family = FONT, opacity = 1 } = options
  return `<text x="${x}" y="${y}" font-family="${family}" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}" fill="${fill}" opacity="${opacity}">${escapeXml(value)}</text>`
}

function box(x, y, width, height, title, options = {}) {
  const {
    lines = [],
    fill = '#ffffff',
    stroke = '#111111',
    strokeWidth = 2,
    rx = 8,
    titleSize = 20,
    lineSize = 15,
    titleColor = '#111111',
    lineColor = '#4a4a4a',
    titleWeight = 600,
    align = 'left',
    padding = 18,
    titleYOffset = 30,
    lineYOffset = 26,
  } = options
  const centerX = x + width / 2
  const anchor = align === 'center' ? 'middle' : 'start'
  const textX = align === 'center' ? centerX : x + padding
  const titleY = y + titleYOffset
  const parts = [`<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="${rx}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`]
  const titleLines = String(title).split('\n')
  titleLines.forEach((line, index) => {
    parts.push(text(textX, titleY + index * (titleSize + 4), line, { size: titleSize, weight: titleWeight, anchor, fill: titleColor }))
  })
  let currentY = titleY + (titleLines.length - 1) * (titleSize + 4) + lineYOffset
  for (const line of lines) {
    parts.push(text(textX, currentY, line, { size: lineSize, anchor, fill: lineColor }))
    currentY += lineSize + 8
  }
  return parts.join('\n')
}

function arrow(x1, y1, x2, y2, options = {}) {
  const { dashed = false, label = '', labelOffsetX = 0, labelOffsetY = -10, width = 2, color = '#111111', labelSize = 14, curve = null } = options
  const dash = dashed ? ' stroke-dasharray="8 6"' : ''
  const path = curve ?? `M ${x1} ${y1} L ${x2} ${y2}`
  const labelPart = label
    ? text((x1 + x2) / 2 + labelOffsetX, (y1 + y2) / 2 + labelOffsetY, label, { size: labelSize, anchor: 'middle', fill: '#555555' })
    : ''
  return `<path d="${path}" fill="none" stroke="${color}" stroke-width="${width}"${dash} marker-end="url(#arrowhead)"/>${labelPart}`
}

function band(x, y, width, height, title, subtitle = '') {
  return [
    `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="14" fill="#f6f6f6" stroke="#c9c9c9" stroke-width="1.5"/>`,
    text(x + 24, y + 34, title, { size: 18, weight: 600, fill: '#222222' }),
    subtitle ? text(x + 24, y + 58, subtitle, { size: 13, fill: '#6b6b6b' }) : '',
  ].join('\n')
}

function svgDocument(width, height, inner, title) {
  return `<!doctype html><html><head><meta charset="utf-8"/><style>
    html, body { margin: 0; padding: 0; background: #ffffff; }
    svg { display: block; }
  </style></head><body>
  <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
    <defs>
      <marker id="arrowhead" markerWidth="12" markerHeight="10" refX="10" refY="5" orient="auto">
        <polygon points="0 0, 12 5, 0 10" fill="#111111"/>
      </marker>
    </defs>
    <rect width="${width}" height="${height}" fill="#ffffff"/>
    ${text(56, 62, title, { size: 32, weight: 700 })}
    ${inner}
    <text x="${width - 56}" y="${height - 26}" font-family="${FONT}" font-size="13" text-anchor="end" fill="#9a9a9a">Task Management System · v1.2.2</text>
  </svg>
  </body></html>`
}

const diagrams = []

// ============ 1. System architecture ============
{
  const width = 1800
  const height = 1180
  const parts = []
  parts.push(band(60, 100, 1520, 250, 'Client Layer', 'Desktop application and LAN browsers'))
  parts.push(box(90, 150, 700, 150, 'Tauri 2 Desktop Shell', { lines: ['Rust window manager · one process · Windows NSIS installer', 'Starts bundled backend, MariaDB and Redis; graceful shutdown'], titleSize: 22 }))
  parts.push(box(840, 150, 690, 150, 'React 18 + TypeScript SPA', { lines: ['Pages · components · CSS Modules · SVG charts', 'Runs inside Tauri WebView2 or any LAN browser'], titleSize: 22 }))
  parts.push(arrow(790, 225, 835, 225, { label: 'WebView2' }))

  parts.push(band(60, 390, 1520, 430, 'Application Layer — FastAPI (Python 3.11)', 'Layered backend: controllers → services → repositories → ORM models'))
  const layerY = 490
  const layerHeight = 230
  const layerWidth = 320
  for (let index = 0; index < 4; index += 1) {
    const layerTitles = ['Controllers / API', 'Services', 'Repositories', 'SQLAlchemy Models']
    const layerLines = [
      ['15 route groups', 'camelCase JSON', 'OpenAPI / Swagger', 'JWT + RBAC'],
      ['Auth · Teams · Tasks', 'Collaboration · Notifications', 'AI assignment · Audit', 'Migrations · Settings'],
      ['Team / Task / Todo', 'Collaboration · AI config', 'Notification', 'Admin / System'],
      ['Users · Teams · Tasks', 'Assignments · Reviews', 'Collaborations · Sub-teams', 'Notifications · Settings'],
    ]
    const x = 95 + index * (layerWidth + 30)
    parts.push(box(x, layerY, layerWidth, layerHeight, layerTitles[index], { lines: layerLines[index], titleSize: 20 }))
    if (index < 3) {
      parts.push(arrow(x + layerWidth + 2, layerY + layerHeight / 2, x + layerWidth + 27, layerY + layerHeight / 2))
    }
  }
  parts.push(box(95, 750, 1450, 50, 'Cross-cutting: permissions · validation · exception handling · Redis cache/rate limit · audit logs', { titleSize: 16, fill: '#f2f2f2', align: 'center', titleYOffset: 32, stroke: '#d0d0d0' }))

  parts.push(band(60, 860, 1520, 230, 'Data & External Services', 'Portable MariaDB / Redis ship inside the installer'))
  parts.push(box(95, 945, 420, 130, 'MariaDB 11.4 (portable)', { lines: ['Relational data: users, teams, tasks, reviews, collaborations, notifications', 'Automatic idempotent schema migration on startup'], titleSize: 16 }))
  parts.push(box(540, 945, 420, 130, 'Redis 5.0 (portable)', { lines: ['Login rate limiting · token blacklist', 'Graceful fallback to in-process memory cache'], titleSize: 16 }))
  parts.push(box(985, 945, 560, 130, 'Optional LLM API (OpenAI-compatible)', { lines: ['DeepSeek / GLM / OpenAI endpoints', 'Only used when configured; local rule engine is the default'], titleSize: 16 }))
  parts.push(arrow(1150, 815, 1240, 940, { label: 'AI client', dashed: true }))
  parts.push(arrow(330, 815, 300, 940, { label: 'SQL', dashed: true }))
  parts.push(arrow(760, 815, 750, 940, { label: 'cache', dashed: true }))
  parts.push(arrow(430, 350, 430, 388, { label: 'HTTP /api/v1 :8765' }))
  parts.push(arrow(1450, 350, 1450, 388, { label: 'LAN access' }))
  diagrams.push({ name: 'architecture.png', width, height, svg: svgDocument(width, height, parts.join('\n'), 'System Architecture') })
}

// ============ 2. Module map ============
{
  const width = 1800
  const height = 1050
  const parts = []
  const columns = [
    {
      title: 'Frontend Modules (React)',
      x: 60,
      items: ['App shell / routing / theme', 'Auth & profile', 'Dashboard & charts', 'Teams & members / levels', 'Tasks & review workflow', 'To-dos & sticky window', 'Collaboration center / sub-teams', 'Notifications & AI configuration', 'Admin console', 'Design system & English UI scan'],
    },
    {
      title: 'Backend Modules (FastAPI)',
      x: 480,
      items: ['Auth / users / permissions', 'Teams & membership / levels', 'Tasks / assignments / reviews', 'Todo & dashboard services', 'Collaboration & sub-teams', 'Notifications', 'AI assignment & configuration', 'Admin & database console', 'Audit logs & system info', 'Database migration service'],
    },
    {
      title: 'Data & Contracts',
      x: 900,
      items: ['MariaDB relational schema', 'SQLAlchemy ORM models', 'Alembic-style idempotent migration', 'Redis cache / rate limit', 'Pydantic request/response schemas', 'camelCase JSON API contracts', 'OpenAPI generated docs', 'Seed / QA datasets'],
    },
    {
      title: 'Runtime & Delivery',
      x: 1320,
      items: ['Tauri 2 Rust shell', 'PyInstaller backend executable', 'Portable MariaDB / Redis', 'NSIS installer + portable ZIP', 'LAN HTTP server', 'Startup health checks', 'Graceful shutdown / process cleanup', 'Verification scripts (16 + 15 + 24 + 21 checks)'],
    },
  ]
  for (const column of columns) {
    parts.push(band(column.x, 100, 390, 880, column.title))
    let itemY = 165
    for (const item of column.items) {
      parts.push(box(column.x + 24, itemY, 342, 50, item, { titleSize: 15, titleYOffset: 31, stroke: '#bdbdbd', fill: '#ffffff' }))
      itemY += 64
    }
  }
  diagrams.push({ name: 'module-map.png', width, height, svg: svgDocument(width, height, parts.join('\n'), 'System Module Map') })
}

// ============ 3. Task lifecycle workflow ============
{
  const width = 1900
  const height = 760
  const parts = []
  const nodes = [
    { x: 70, y: 220, w: 230, h: 110, title: 'Publisher', lines: ['Team admin / sub-admin', 'publishes a task'] },
    { x: 360, y: 220, w: 230, h: 110, title: 'Published', lines: ['Assignees selected', 'Pending acceptance'] },
    { x: 650, y: 110, w: 220, h: 100, title: 'Accepted', lines: ['Assignee to-do created'] },
    { x: 650, y: 330, w: 220, h: 100, title: 'Declined', lines: ['Optional acceptance only'] },
    { x: 940, y: 220, w: 230, h: 110, title: 'In Progress', lines: ['Execution tracked', 'Progress 0-100%'] },
    { x: 1230, y: 220, w: 230, h: 110, title: 'Pending Review', lines: ['Assignee submitted', 'Reviewer notified'] },
    { x: 1520, y: 110, w: 230, h: 100, title: 'Archived', lines: ['Approved & closed'] },
    { x: 1520, y: 360, w: 230, h: 100, title: 'Rework', lines: ['Rejected with comment'] },
  ]
  for (const node of nodes) parts.push(box(node.x, node.y, node.w, node.h, node.title, { lines: node.lines, align: 'center', titleYOffset: 34, titleSize: 19 }))
  parts.push(arrow(300, 275, 355, 275))
  parts.push(arrow(590, 250, 645, 175, { label: 'accept', labelOffsetY: -12 }))
  parts.push(arrow(590, 300, 645, 375, { label: 'decline', labelOffsetY: 16 }))
  parts.push(arrow(870, 175, 935, 235, {}))
  parts.push(arrow(870, 370, 935, 300, {}))
  parts.push(arrow(1170, 275, 1225, 275))
  parts.push(arrow(1460, 245, 1515, 175, { label: 'approve', labelOffsetY: -10 }))
  parts.push(arrow(1460, 305, 1515, 395, { label: 'reject', labelOffsetY: 18 }))
  parts.push(arrow(1635, 460, 1635, 520, { color: '#111111' }))
  parts.push(`<path d="M 1635 520 L 1055 520 L 1055 335" fill="none" stroke="#111111" stroke-width="2" marker-end="url(#arrowhead)"/>`)
  parts.push(text(1345, 545, 'rework returns to execution', { size: 14, anchor: 'middle', fill: '#555555' }))
  parts.push(box(70, 600, 1680, 100, 'Cancellation and audit', { lines: ['Publisher may cancel a published / in-progress task. Every review is recorded with reviewer, result, comment and timestamp.', 'All state transitions are validated by the service layer; notifications are emitted for assignment, submission, approval and rejection.'], titleSize: 20 }))
  diagrams.push({ name: 'task-lifecycle.png', width, height, svg: svgDocument(width, height, parts.join('\n'), 'Core User Workflow — Task Lifecycle') })
}

// ============ 4. Collaboration & dual review workflow ============
{
  const width = 2000
  const height = 900
  const parts = []
  parts.push(box(60, 100, 1880, 150, 'Phase A — Establish collaboration', { lines: ['Initiator unit (team or sub-team) submits a request and names its liaison → receiver admin confirms and designates its liaison → collaboration becomes active'], titleSize: 22 }))
  const phaseAY = 200
  const phaseA = [
    { x: 90, title: 'Initiate Request', lines: ['Initiator liaison named'] },
    { x: 470, title: 'Receiver Admin Review', lines: ['Confirm or reject'] },
    { x: 850, title: 'Collaboration Active', lines: ['Both liaisons confirmed'] },
    { x: 1230, title: 'Team Directory', lines: ['Discoverable partners'] },
  ]
  for (const item of phaseA) {
    parts.push(box(item.x, phaseAY, 300, 90, item.title, { lines: item.lines, align: 'center', titleSize: 17, titleYOffset: 32 }))
  }
  parts.push(arrow(390, phaseAY + 45, 465, phaseAY + 45))
  parts.push(arrow(770, phaseAY + 45, 845, phaseAY + 45))
  parts.push(arrow(1150, phaseAY + 45, 1225, phaseAY + 45))

  parts.push(box(60, 340, 1880, 500, 'Phase B — Collaboration task and two-stage review', { lines: [], titleSize: 22 }))
  const phaseB = [
    { x: 95, y: 430, w: 250, title: 'Dispatch Task', lines: ['Initiator publishes', 'collaboration task'] },
    { x: 390, y: 430, w: 250, title: 'Receiver Confirms', lines: ['Liaison accepts', 'and assigns executors'] },
    { x: 685, y: 430, w: 250, title: 'Execution', lines: ['Assignees work', 'and submit'] },
    { x: 980, y: 430, w: 250, title: 'Receiver Review', lines: ['Liaison approves', 'or requests changes'] },
    { x: 1275, y: 430, w: 250, title: 'Initiator Review', lines: ['Publisher gives', 'final approval'] },
    { x: 1570, y: 430, w: 250, title: 'Archived', lines: ['Both sides notified'] },
  ]
  for (const item of phaseB) parts.push(box(item.x, item.y, item.w, 140, item.title, { lines: item.lines, align: 'center', titleSize: 17, titleYOffset: 34 }))
  for (let index = 0; index < phaseB.length - 1; index += 1) {
    parts.push(arrow(phaseB[index].x + 252, 500, phaseB[index + 1].x - 4, 500))
  }
  parts.push(`<path d="M 1105 570 L 1105 640 L 810 640 L 810 575" fill="none" stroke="#111111" stroke-width="2" stroke-dasharray="8 6" marker-end="url(#arrowhead)"/>`)
  parts.push(text(1110, 660, 'reject → rework with comment', { size: 15, anchor: 'middle', fill: '#555555' }))
  parts.push(text(1000, 720, 'If either review rejects, the task returns to execution and all participants receive a notification.', { size: 15, anchor: 'middle', fill: '#555555' }))
  diagrams.push({ name: 'collaboration-workflow.png', width, height, svg: svgDocument(width, height, parts.join('\n'), 'Core User Workflow — Collaboration & Dual Review') })
}

// ============ 5. Time boxing timeline ============
{
  const width = 1900
  const height = 820
  const parts = []
  const boxes = [
    { x: 70, title: 'Time Box 1 · Demo Baseline', dates: 'Nov 15 – Nov 18', lines: ['Team, task, review, to-do & dashboard', 'FastAPI layering + MariaDB schema', 'Deliverable: internal demo v1.0'], evidence: 'pytest 63 · E2E 12' },
    { x: 500, title: 'Time Box 2 · Collaboration', dates: 'Nov 19 – Nov 21', lines: ['Team / sub-team collaboration', 'Liaisons, dual review, notifications', 'Deliverable: v1.1.0'], evidence: 'pytest 123 · E2E 18' },
    { x: 930, title: 'Time Box 3 · AI Module', dates: 'Nov 22 – Nov 23', lines: ['Local rule engine + LLM fallback', 'Four dispatch modes, auto-assignment', 'Deliverable: v1.1.1'], evidence: 'pytest 136 · AI tests 54' },
    { x: 1360, title: 'Time Box 4 · Hardening & QA', dates: 'Nov 24 – Nov 25', lines: ['English UI, sticky fix, visual QA', 'Packaging + installer verification', 'Deliverable: v1.2.2'], evidence: 'QA 33 + 29 · checks 76' },
  ]
  parts.push(`<line x1="100" y1="170" x2="1800" y2="170" stroke="#111111" stroke-width="3"/>`)
  for (let index = 0; index < boxes.length; index += 1) {
    const item = boxes[index]
    parts.push(`<circle cx="${item.x + 180}" cy="170" r="12" fill="#111111"/>`)
    parts.push(text(item.x + 180, 135, item.dates, { size: 18, anchor: 'middle', weight: 600 }))
    parts.push(box(item.x, 220, 420, 250, item.title, { lines: item.lines, titleSize: 20 }))
    parts.push(box(item.x, 500, 420, 90, 'Evidence', { lines: [item.evidence], titleSize: 16, fill: '#f4f4f4', stroke: '#c9c9c9' }))
  }
  parts.push(box(70, 640, 1760, 120, 'Time-boxing rules used by the team', { lines: ['Each box has a fixed outcome, demo and verification gate; unfinished items move to the next box instead of extending the deadline.', 'Daily 15-minute sync · contract-first API documents · automated regression before each demo · retrospectives after every box.'], titleSize: 20, fill: '#fafafa' }))
  diagrams.push({ name: 'timeboxing.png', width, height, svg: svgDocument(width, height, parts.join('\n'), 'Development Process — Time Boxing') })
}

// ============ 6. Process improvement evidence ============
{
  const width = 1800
  const height = 1120
  const parts = []
  parts.push(box(60, 100, 810, 430, 'Verification coverage growth', { lines: [], titleSize: 22 }))
  const bars = [
    { label: 'Backend tests', before: 63, after: 136 },
    { label: 'Browser E2E', before: 12, after: 21 },
    { label: 'Human-like UI checks', before: 0, after: 62 },
    { label: 'Installer checks', before: 16, after: 76 },
  ]
  const chartX = 110
  const chartBaseY = 465
  const maxValue = 140
  const scale = 290 / maxValue
  for (let index = 0; index < bars.length; index += 1) {
    const bar = bars[index]
    const groupX = chartX + index * 190
    const beforeHeight = Math.max(2, bar.before * scale)
    const afterHeight = Math.max(2, bar.after * scale)
    parts.push(`<rect x="${groupX}" y="${chartBaseY - beforeHeight}" width="52" height="${beforeHeight}" fill="#c9c9c9"/>`)
    parts.push(`<rect x="${groupX + 62}" y="${chartBaseY - afterHeight}" width="52" height="${afterHeight}" fill="#111111"/>`)
    parts.push(text(groupX + 26, chartBaseY - beforeHeight - 8, String(bar.before), { size: 14, anchor: 'middle', fill: '#777777' }))
    parts.push(text(groupX + 88, chartBaseY - afterHeight - 8, String(bar.after), { size: 14, anchor: 'middle', weight: 600 }))
    parts.push(text(groupX + 57, chartBaseY + 26, bar.label, { size: 13, anchor: 'middle', fill: '#444444' }))
  }
  parts.push(text(110, 515, 'grey = initial demo · black = final v1.2.2', { size: 13, fill: '#777777' }))
  parts.push(box(900, 100, 840, 430, 'Quality gates at final release', { lines: ['0 failing automated tests', '0 unexpected console errors in QA', '0 Chinese UI strings (AST checks)', '181 frontend files and the whole backend scanned', '76 / 76 installer acceptance checks', '0 blocking defects in final QA', 'All six access roles verified'], titleSize: 22 }))
  parts.push(box(60, 575, 1680, 160, 'Process improvements and evidence', { lines: ['Contract-first: 8 living contract documents (DB, API, collaboration, AI, frontend design) reviewed before implementation.', 'Parallel work streams: scoped ownership, shared task board and per-module regression gates (4 frontend, 4 backend, 1 packaging).', 'Automated gates: 136 backend tests, 21 E2E tests, 62 human-like UI checks, 4 packaging verification scripts.'], titleSize: 20 }))
  parts.push(box(60, 770, 820, 250, 'Defects found and closed', { lines: ['Sticky window deadlock: synchronous Tauri command caused', 'a UI freeze; fixed with async window creation, verified', 'on the installed application.', 'Toast overlay blocked header controls: moved below the top', 'bar, verified with UIA bounding boxes.', 'Sticky header crowded at 380 px: two-row header and', 'nowrap counters, verified by real-device style checks.'], titleSize: 20 }))
  parts.push(box(920, 770, 820, 250, 'Effect on delivery confidence', { lines: ['Backlog slicing by time box kept demos on schedule', '(4 boxes in 11 days).', 'Every iteration ended with a deployable Windows build', 'and a written acceptance record.', 'Final package: 31.13 MB installer, 40.57 MB portable zip.', 'Known boundaries documented: unsigned installer,', 'Windows-first packaging, real LLM API pending.'], titleSize: 20 }))
  diagrams.push({ name: 'process-improvement.png', width, height, svg: svgDocument(width, height, parts.join('\n'), 'Process Improvement Evidence') })
}

// ============ 7. Runtime & packaging ============
{
  const width = 1800
  const height = 980
  const parts = []
  parts.push(box(60, 100, 780, 330, 'Installed application bundle', { lines: ['task-management-desktop.exe (Tauri)', 'resources/backend/runServer.exe (PyInstaller)', 'resources/runtime/mariadb/ + redis/', 'resources/frontend/index.html + assets/'], titleSize: 22 }))
  parts.push(box(900, 100, 840, 330, 'First-run startup sequence', { lines: ['1  Tauri shell starts hidden', '2  runServer --manage-runtime launches bundled MariaDB and Redis', '3  Alembic-style migration creates / upgrades database schema', '4  health check /api/v1/health passes → main window shown', '5  same HTTP server exposes the SPA for LAN clients'], titleSize: 22 }))
  parts.push(box(60, 500, 560, 360, 'Shutdown contract', { lines: ['Window close triggers backend stdin EOF.', 'Backend stops MariaDB and Redis it started.', 'If a port is occupied, bundled services auto-increment.', 'Ports and child processes are verified clean by packaging scripts.'], titleSize: 20 }))
  parts.push(box(660, 500, 560, 360, 'Updates and data safety', { lines: ['Idempotent migration adds only missing tables / columns / indexes.', 'v1.0 → v1.2.2 upgrade keeps existing users and team data.', 'Installer and portable ZIP share the same build.', 'SHA-256 checksums are published for all artifacts.'], titleSize: 20 }))
  parts.push(box(1260, 500, 480, 360, 'Verification scripts', { lines: ['verifyInstalledApp.ps1 — 16 checks', 'verifyStickyWindow.ps1 — 15 checks', 'verifyUpgradePath.ps1 — 24 checks', 'verifyDesktopStyles.ps1 — 21 checks'], titleSize: 20 }))
  diagrams.push({ name: 'runtime-packaging.png', width, height, svg: svgDocument(width, height, parts.join('\n'), 'Desktop Runtime & Packaging') })
}


// ============ 8. AI auto-assignment flow ============
{
  const width = 1900
  const height = 960
  const parts = []
  parts.push(box(70, 110, 330, 120, 'Task published', { lines: ['Title, description, priority', 'required skills, team context'], titleSize: 22, align: 'center' }))
  parts.push(box(470, 110, 360, 120, 'Candidate pool', { lines: ['Role and level permissions', 'exclude publisher and inactive users'], titleSize: 22, align: 'center' }))
  parts.push(box(900, 110, 430, 120, 'Dispatch modes', { lines: ['LOCAL_ONLY · LLM_ONLY · LOCAL_FIRST · LLM_FIRST', 'fallback on failure or empty result'], titleSize: 20, align: 'center' }))
  parts.push(arrow(400, 170, 465, 170))
  parts.push(arrow(830, 170, 895, 170))

  parts.push(box(120, 330, 650, 330, 'Local rule engine', { lines: ['Score = round(skill match ratio × 100) − active to-dos × workload penalty', 'Zero skill overlap excluded; score below threshold excluded', 'Stable ordering: score ↓, active to-dos ↑, user ID ↑', 'Returns up to 10 candidates with matched skills and reasons'], titleSize: 22 }))
  parts.push(box(900, 330, 830, 330, 'Optional LLM path (OpenAI-compatible)', { lines: ['Chat completion receives the candidate list and required skills', 'Returns ranked user IDs and a short reason (JSON only)', 'Malformed JSON, timeout or HTTP error raises a route error', 'Dispatcher falls back according to the selected mode', 'API key is masked in the UI and never logged'], titleSize: 22 }))
  parts.push(arrow(615, 235, 445, 325, { label: 'default route' }))
  parts.push(arrow(1115, 235, 1315, 325, { label: 'optional re-rank', dashed: true }))

  parts.push(box(470, 730, 960, 120, 'Outcome and notifications', { lines: ['Assigned: task starts in progress, executor and matched candidates are notified', 'Unassigned: task stays published with manual-assign flag and the publisher is notified'], titleSize: 22, align: 'center' }))
  parts.push(arrow(445, 660, 720, 725))
  parts.push(arrow(1315, 660, 1100, 725))
  parts.push(text(1000, 900, 'Evaluation: 17 assignment tests · 12 LLM tests · 8 notification integration tests · 9 configuration tests', { size: 15, anchor: 'middle', fill: '#666666' }))
  diagrams.push({ name: 'ai-assignment.png', width, height, svg: svgDocument(width, height, parts.join('\n'), 'AI Auto-Assignment Design') })
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })
for (const diagram of diagrams) {
  const page = await browser.newPage({ viewport: { width: diagram.width, height: diagram.height }, deviceScaleFactor: 2 })
  await page.setContent(diagram.svg, { waitUntil: 'load' })
  const outputPath = path.join(outputDirectory, diagram.name)
  await page.screenshot({ path: outputPath, clip: { x: 0, y: 0, width: diagram.width, height: diagram.height } })
  console.log('[diagram] ' + path.relative(projectRoot, outputPath))
  await page.close()
}
await browser.close()
console.log('Generated ' + diagrams.length + ' diagrams into ' + outputDirectory)
