/**
 * Cross-platform Playwright webServer entry point.
 *
 * The old config used `VITE_API_URL=... npm run build && npm run preview`,
 * which works in bash but fails in Windows cmd.exe. This helper sets the env
 * from Node and spawns npm without relying on shell syntax.
 */
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const webDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm'
const env = {
  ...process.env,
  VITE_API_URL: process.env.E2E_API_URL || 'http://localhost:8000',
}

function run(args) {
  return new Promise((resolve, reject) => {
    const child = spawn(npmCommand, args, {
      cwd: webDir,
      env,
      stdio: 'inherit',
      shell: process.platform === 'win32',
    })
    const forward = (signal) => {
      if (!child.killed) child.kill(signal)
    }
    process.on('SIGINT', forward)
    process.on('SIGTERM', forward)
    child.on('error', reject)
    child.on('exit', (code) => {
      process.off('SIGINT', forward)
      process.off('SIGTERM', forward)
      resolve(code ?? 1)
    })
  })
}

const buildCode = await run(['run', 'build'])
if (buildCode !== 0) process.exit(buildCode)
const previewCode = await run(['run', 'preview', '--', '--port', '5173', '--strictPort'])
process.exit(previewCode)
