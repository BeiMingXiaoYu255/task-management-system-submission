/**
 * 前端 UI 英文化检测脚本：扫描 src 下全部 .ts/.tsx，找出用户可见的字符串/JSX 文本中的中文。
 *
 * 说明：
 * 1. 使用 TypeScript 编译器 AST，只检查字符串字面量、模板字符串片段与 JSX 文本；
 * 2. 代码注释（// 与 /* *\/）不会被检查，允许保留中文注释；
 * 3. 发现中文时输出 文件:行号:片段 并以退出码 1 结束，便于 CI/智能体验收；
 * 4. 用法：cd Frontend && node checkEnglishUi.mjs
 */

import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const ts = require('typescript')

const sourceRootDirectory = path.resolve('src')
const chineseCharacterPattern = /[\u3400-\u9fff\uf900-\ufaff]/
const supportedExtensions = new Set(['.ts', '.tsx'])

/** 递归收集源码文件。 */
function collectSourceFiles(directoryPath) {
  const collectedFiles = []
  for (const entry of fs.readdirSync(directoryPath, { withFileTypes: true })) {
    const entryPath = path.join(directoryPath, entry.name)
    if (entry.isDirectory()) {
      collectedFiles.push(...collectSourceFiles(entryPath))
    } else if (supportedExtensions.has(path.extname(entry.name))) {
      collectedFiles.push(entryPath)
    }
  }
  return collectedFiles
}

/** 判断节点文本是否包含中文。 */
function containsChinese(text) {
  return typeof text === 'string' && chineseCharacterPattern.test(text)
}

/** 提取节点中用于展示的字符串文本。 */
function extractDisplayText(node) {
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
    return node.text
  }
  if (ts.isTemplateHead(node) || ts.isTemplateMiddle(node) || ts.isTemplateTail(node)) {
    return node.text
  }
  if (ts.isJsxText(node)) {
    return node.text
  }
  return null
}

const findings = []

/** 递归遍历 AST 节点收集发现项。 */
function visitNode(node, sourceFile) {
  const displayText = extractDisplayText(node)
  if (displayText !== null && containsChinese(displayText)) {
    const position = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile))
    findings.push({
      file: path.relative(process.cwd(), sourceFile.fileName),
      line: position.line + 1,
      text: displayText.trim().replace(/\s+/g, ' ').slice(0, 140),
    })
  }
  ts.forEachChild(node, (childNode) => visitNode(childNode, sourceFile))
}

const sourceFiles = collectSourceFiles(sourceRootDirectory)
for (const filePath of sourceFiles) {
  const fileContent = fs.readFileSync(filePath, 'utf8')
  const sourceFile = ts.createSourceFile(
    filePath,
    fileContent,
    ts.ScriptTarget.Latest,
    true,
    filePath.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  )
  visitNode(sourceFile, sourceFile)
}

if (findings.length === 0) {
  console.log('OK: frontend source contains no Chinese UI strings (' + sourceFiles.length + ' files checked).')
  process.exit(0)
}

console.log('Found ' + findings.length + ' Chinese UI strings:')
for (const finding of findings) {
  console.log(finding.file + ':' + finding.line + ': ' + finding.text)
}
process.exit(1)
