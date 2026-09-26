import { cp, mkdir, rm } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const require = createRequire(import.meta.url)
const sourceRoot = dirname(require.resolve('pdfjs-dist/package.json'))
const publicRoot = fileURLToPath(new URL('../public/pdfjs/', import.meta.url))

// Keep these resources in sync with the installed PDF.js version. Vite serves
// public files in development and copies them into the production build.
export async function copyPdfAssets(targetRoot = publicRoot) {
  await mkdir(targetRoot, { recursive: true })
  for (const directory of ['cmaps', 'standard_fonts']) {
    const target = join(targetRoot, directory)
    await rm(target, { recursive: true, force: true })
    await cp(join(sourceRoot, directory), target, { recursive: true })
  }
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  await copyPdfAssets()
}
