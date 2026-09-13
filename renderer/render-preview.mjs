import fs from 'node:fs/promises'
import http from 'node:http'
import path from 'node:path'
import process from 'node:process'

import chromium from '@sparticuz/chromium'
import puppeteer from 'puppeteer-core'

const MIME = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.stl': 'application/octet-stream',
  '.urdf': 'application/xml; charset=utf-8',
  '.webp': 'image/webp',
}

const args = parseArgs(process.argv.slice(2))
if (!args.dist || !args.models || !args.output) {
  throw new Error('用法：render-preview.mjs --dist <dir> --models <dir> --output <file>')
}

const payload = JSON.parse(await readStdin())
const distRoot = path.resolve(args.dist)
const modelsRoot = path.resolve(args.models)
const output = path.resolve(args.output)
const server = createStaticServer(distRoot, modelsRoot)
let browser

try {
  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  const address = server.address()
  const encoded = Buffer.from(JSON.stringify(payload), 'utf8').toString('base64url')
  const url = `http://127.0.0.1:${address.port}/preview-render.html#${encoded}`

  browser = await puppeteer.launch({
    args: chromium.args,
    executablePath: await chromium.executablePath(),
    headless: 'shell',
  })
  const page = await browser.newPage()
  await page.setViewport({ width: 1200, height: 800, deviceScaleFactor: 1 })
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30_000 })
  await page.waitForFunction(
    () => window.__PREVIEW_READY__ || window.__PREVIEW_ERROR__,
    { timeout: 180_000, polling: 200 },
  )
  const error = await page.evaluate(() => window.__PREVIEW_ERROR__)
  if (error) throw new Error(error)
  const preview = await page.$('#preview')
  if (!preview) throw new Error('渲染页面缺少预览画布')
  await fs.mkdir(path.dirname(output), { recursive: true })
  await preview.screenshot({ path: output, type: 'webp', quality: 78 })
} finally {
  await browser?.close()
  await new Promise((resolve) => server.close(resolve))
}

function createStaticServer(frontendRoot, robotModelsRoot) {
  return http.createServer(async (request, response) => {
    try {
      const requestPath = decodeURIComponent(new URL(request.url, 'http://127.0.0.1').pathname)
      const mapping = requestPath.startsWith('/models/')
        ? { root: robotModelsRoot, relative: requestPath.slice('/models/'.length) }
        : { root: frontendRoot, relative: requestPath.replace(/^\//, '') || 'preview-render.html' }
      const file = safeResolve(mapping.root, mapping.relative)
      const stat = await fs.stat(file)
      if (!stat.isFile()) throw new Error('not a file')
      response.writeHead(200, {
        'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream',
        'Content-Length': stat.size,
        'Cache-Control': 'no-store',
      })
      const body = await fs.readFile(file)
      response.end(body)
    } catch {
      response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' })
      response.end('not found')
    }
  })
}

function safeResolve(root, relative) {
  const resolvedRoot = path.resolve(root)
  const target = path.resolve(resolvedRoot, relative)
  if (target !== resolvedRoot && !target.startsWith(`${resolvedRoot}${path.sep}`)) {
    throw new Error('invalid path')
  }
  return target
}

function parseArgs(values) {
  const out = {}
  for (let index = 0; index < values.length; index += 2) {
    const key = values[index]?.replace(/^--/, '')
    if (key) out[key] = values[index + 1]
  }
  return out
}

async function readStdin() {
  let input = ''
  process.stdin.setEncoding('utf8')
  for await (const chunk of process.stdin) input += chunk
  return input
}
