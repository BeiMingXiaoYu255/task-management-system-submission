import fs from 'node:fs'
import path from 'node:path'
import { chromium } from '@playwright/test'

const projectRoot = path.resolve(process.cwd(), '..')
const assetsDirectory = path.join(projectRoot, 'deliverables', 'assets')
const outputPath = path.join(assetsDirectory, 'ui-collage.png')

const items = [
  ['ui-dashboard.png', 'Dashboard and task analytics'],
  ['ui-team-tasks.png', 'Team tasks and review state'],
  ['ui-task-form-ai.png', 'Publish task with AI recommendation'],
  ['ui-collaboration-center.png', 'Team collaboration center'],
  ['ui-ai-config.png', 'AI configuration and connectivity test'],
  ['ui-admin-overview.png', 'Administration console'],
]

function toDataUri(fileName) {
  const filePath = path.join(assetsDirectory, fileName)
  return 'data:image/png;base64,' + fs.readFileSync(filePath).toString('base64')
}

const cards = items.map(([fileName, label]) => `
  <figure>
    <div class="frame"><img src="${toDataUri(fileName)}" alt="${label}"/></div>
    <figcaption>${label}</figcaption>
  </figure>`).join('\n')

const html = `<!doctype html><html><head><meta charset="utf-8"/><style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: #ffffff; font-family: 'Segoe UI', Arial, sans-serif; color: #111; }
  .page { width: 1800px; height: 1120px; padding: 40px 48px 32px; display: flex; flex-direction: column; gap: 20px; }
  h1 { margin: 0; font-size: 34px; letter-spacing: -0.3px; }
  .subtitle { margin: 0; font-size: 17px; color: #666; }
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; flex: 1; }
  figure { margin: 0; display: flex; flex-direction: column; gap: 8px; min-height: 0; }
  .frame { flex: 1; border: 1.5px solid #111; border-radius: 8px; overflow: hidden; background: #f7f7f7; min-height: 0; }
  img { width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }
  figcaption { font-size: 15px; color: #333; font-weight: 600; }
  .footer { display: flex; justify-content: space-between; font-size: 12px; color: #999; }
</style></head><body>
<div class="page">
  <div>
    <h1>Task Management System — Interface Overview</h1>
    <p class="subtitle">Desktop application and LAN web interface · grayscale by design · English UI</p>
  </div>
  <div class="grid">${cards}</div>
  <div class="footer"><span>Task Management System v1.2.2</span><span>Screenshots captured during human-style QA acceptance</span></div>
</div>
</body></html>`

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 1800, height: 1120 }, deviceScaleFactor: 2 })
await page.setContent(html, { waitUntil: 'load' })
await page.screenshot({ path: outputPath })
await browser.close()
console.log('collage generated: ' + outputPath)
