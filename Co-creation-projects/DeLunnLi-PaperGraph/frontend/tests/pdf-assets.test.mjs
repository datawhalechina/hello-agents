import { after, before, test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, sep } from 'node:path'
import { getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs'
import { copyPdfAssets } from '../scripts/copy-pdf-assets.mjs'

let assets
before(async () => {
  assets = await mkdtemp(join(tmpdir(), 'papergraph-pdf-assets-'))
  await copyPdfAssets(assets)
})
after(async () => { if (assets) await rm(assets, { recursive: true, force: true }) })

// A tiny valid PDF using a predefined Japanese CMap, without an embedded
// ToUnicode map. PDF.js needs UniJIS-UCS2-H.bcmap to decode this text.
function japanesePdf() {
  const text = 'BT /F1 20 Tf 20 80 Td <65e5672c8a9e> Tj ET'
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 150] /Resources << /Font << /F1 4 0 R >> >> /Contents 7 0 R >>',
    '<< /Type /Font /Subtype /Type0 /BaseFont /HeiseiMin-W3 /Encoding /UniJIS-UCS2-H /DescendantFonts [5 0 R] >>',
    '<< /Type /Font /Subtype /CIDFontType0 /BaseFont /HeiseiMin-W3 /CIDSystemInfo << /Registry (Adobe) /Ordering (Japan1) /Supplement 5 >> /FontDescriptor 6 0 R /DW 1000 >>',
    '<< /Type /FontDescriptor /FontName /HeiseiMin-W3 /Flags 6 /FontBBox [0 -200 1000 900] /ItalicAngle 0 /Ascent 880 /Descent -120 /CapHeight 700 /StemV 80 >>',
    `<< /Length ${text.length} >>\nstream\n${text}\nendstream`,
  ]
  let content = '%PDF-1.4\n'
  const offsets = [0]
  for (const [index, object] of objects.entries()) {
    offsets.push(content.length)
    content += `${index + 1} 0 obj\n${object}\nendobj\n`
  }
  const xref = content.length
  content += `xref\n0 ${offsets.length}\n0000000000 65535 f \n`
  content += offsets.slice(1).map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')
  content += `trailer\n<< /Size ${offsets.length} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`
  return new TextEncoder().encode(content)
}

test('copies both PDF asset families and their license files', async () => {
  for (const file of ['cmaps/UniJIS-UCS2-H.bcmap', 'cmaps/LICENSE', 'standard_fonts/LiberationSans-Regular.ttf', 'standard_fonts/LICENSE_LIBERATION']) {
    assert.ok((await readFile(join(assets, file))).length > 0, file)
  }
})

test('real PDF.js decodes Japanese text with the generated CMaps', async () => {
  const task = getDocument({
    data: japanesePdf(),
    cMapUrl: join(assets, 'cmaps') + sep,
    cMapPacked: true,
    standardFontDataUrl: join(assets, 'standard_fonts') + sep,
    useSystemFonts: false,
  })
  try {
    const document = await task.promise
    const page = await document.getPage(1)
    const content = await page.getTextContent()
    assert.equal(content.items.map((item) => item.str || '').join(''), '日本語')
  } finally {
    await task.destroy()
  }
})
