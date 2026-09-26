import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, reactive, type App } from 'vue'
import PdfJsViewer from '../src/components/PdfJsViewer.vue'

const pdf = vi.hoisted(() => ({ backendOrigin: '', getDocument: vi.fn(), render: vi.fn(), textRender: vi.fn(), cancel: vi.fn() }))
vi.mock('../src/config/ports', () => ({ get BACKEND_ORIGIN() { return pdf.backendOrigin } }))
vi.mock('pdfjs-dist', () => ({
  getDocument: pdf.getDocument,
  GlobalWorkerOptions: {},
  TextLayer: class {
    container: HTMLElement
    constructor({ container }: { container: HTMLElement }) { this.container = container }
    async render() { await pdf.textRender(); this.container.textContent = 'Selectable paper text' }
    cancel = pdf.cancel
  },
}))

const deferred = <T,>() => {
  let resolve!: (value: T) => void
  let reject!: (reason: Error) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const makeDocument = () => ({
  numPages: 3,
  getPage: vi.fn(async () => ({
    getViewport: ({ scale }: { scale: number }) => ({ width: 600 * scale, height: 800 * scale }),
    render: pdf.render,
    getTextContent: vi.fn(async () => ({ items: [] })),
  })),
})
let app: App | undefined
let host: HTMLDivElement
const mount = (src = '/api/papers/1/pdf') => {
  const state = reactive({ src, page: 1 })
  const loaded = vi.fn()
  const error = vi.fn()
  app = createApp({ render: () => h(PdfJsViewer, { ...state, onLoaded: loaded, onError: error }) })
  app.component('AButton', defineComponent({ setup(_, { slots, attrs }) { return () => h('button', attrs, slots.default?.()) } }))
  app.component('AInputNumber', defineComponent({ inheritAttrs: false, setup() { return () => h('input') } }))
  app.component('ASpin', defineComponent({ setup() { return () => h('span', 'loading') } }))
  app.mount(host)
  return { state, loaded, error }
}
const click = async (text: string) => {
  const button = Array.from(host.querySelectorAll('button')).find((item) => item.textContent === text)
  expect(button).toBeDefined()
  button!.click()
  await nextTick()
}

beforeEach(() => {
  vi.clearAllMocks()
  pdf.backendOrigin = ''
  host = document.createElement('div')
  document.body.append(host)
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({} as CanvasRenderingContext2D)
  HTMLElement.prototype.scrollTo = () => {}
  pdf.render.mockImplementation(() => ({ promise: Promise.resolve(), cancel: pdf.cancel }))
  pdf.textRender.mockResolvedValue(undefined)
  pdf.getDocument.mockImplementation(() => ({ promise: Promise.resolve(makeDocument()), destroy: vi.fn(async () => {}) }))
})
afterEach(() => { app?.unmount(); app = undefined; host.remove(); vi.restoreAllMocks() })

describe('PDF reader', () => {
  it('emits loaded only after canvas and selectable text have rendered', async () => {
    const drawing = deferred<void>()
    const text = deferred<void>()
    pdf.render.mockReturnValue({ promise: drawing.promise, cancel: pdf.cancel })
    pdf.textRender.mockReturnValue(text.promise)
    const { loaded } = mount()
    await vi.waitFor(() => expect(pdf.render).toHaveBeenCalledOnce())
    expect(loaded).not.toHaveBeenCalled()
    drawing.resolve()
    await vi.waitFor(() => expect(pdf.textRender).toHaveBeenCalledOnce())
    expect(loaded).not.toHaveBeenCalled()
    text.resolve()
    await vi.waitFor(() => expect(loaded).toHaveBeenCalledOnce())
    expect(host.querySelector('.textLayer')?.textContent).toContain('Selectable paper text')
    expect(host.querySelector('iframe')).toBeNull()
  })

  it('renders the requested page, clamps out-of-range pages, and changes zoom', async () => {
    const document = makeDocument()
    pdf.getDocument.mockReturnValue({ promise: Promise.resolve(document), destroy: vi.fn(async () => {}) })
    const { loaded, state } = mount()
    await vi.waitFor(() => expect(loaded).toHaveBeenCalledOnce())
    await click('下一页')
    await vi.waitFor(() => expect(host.querySelector('canvas')?.getAttribute('aria-label')).toBe('PDF 第 2 页'))
    await vi.waitFor(() => expect(host.querySelector('.pdf-stage')?.getAttribute('aria-busy')).toBe('false'))
    await click('＋')
    await vi.waitFor(() => expect(host.querySelector('canvas')?.style.width).toBe('780px'))
    state.page = 99
    await vi.waitFor(() => expect(document.getPage).toHaveBeenLastCalledWith(3))
    expect(loaded).toHaveBeenCalledOnce()
  })

  it.each(['http://127.0.0.1:8000', 'https://papergraph-api.example'])('loads PDFs from the configured backend %s', async (origin) => {
    pdf.backendOrigin = origin
    const { loaded, error } = mount(`${origin}/api/papers/1/pdf`)
    await vi.waitFor(() => expect(loaded).toHaveBeenCalledOnce())
    expect(error).not.toHaveBeenCalled()
    expect(pdf.getDocument).toHaveBeenCalledWith({
      url: `${origin}/api/papers/1/pdf`, withCredentials: false,
      cMapUrl: '/pdfjs/cmaps/', cMapPacked: true, standardFontDataUrl: '/pdfjs/standard_fonts/',
    })
  })

  it.each(['https://external.example/paper.pdf', 'data:application/pdf;base64,AA==', 'blob:http://localhost:3000/test'])('rejects untrusted PDF URL %s without downloading it', async (src) => {
    const { error, loaded } = mount(src)
    await vi.waitFor(() => expect(error).toHaveBeenCalledOnce())
    expect(pdf.getDocument).not.toHaveBeenCalled()
    expect(loaded).not.toHaveBeenCalled()
    expect(host.querySelector('[role="alert"]')?.textContent).toContain('仅允许加载本站或已配置后端的 PDF')
  })

  it('uses the deployment base for PDF resources', async () => {
    vi.stubEnv('BASE_URL', '/papergraph/')
    try {
      const { loaded } = mount()
      await vi.waitFor(() => expect(loaded).toHaveBeenCalledOnce())
      expect(pdf.getDocument).toHaveBeenCalledWith(expect.objectContaining({
        cMapUrl: '/papergraph/pdfjs/cmaps/',
        standardFontDataUrl: '/papergraph/pdfjs/standard_fonts/',
      }))
    } finally {
      vi.unstubAllEnvs()
    }
  })

  it('reports invalid PDFs and supports retry', async () => {
    pdf.getDocument.mockImplementationOnce(() => ({ promise: Promise.reject(new Error('Invalid PDF')), destroy: vi.fn(async () => {}) }))
    const { error, loaded } = mount()
    await vi.waitFor(() => expect(error).toHaveBeenCalledOnce())
    expect(loaded).not.toHaveBeenCalled()
    await click('重新加载')
    await vi.waitFor(() => expect(loaded).toHaveBeenCalledOnce())
    expect(host.querySelector('[role="alert"]')).toBeNull()
  })

  it('reports a canvas rendering failure without claiming the PDF loaded', async () => {
    pdf.render.mockImplementationOnce(() => ({ promise: Promise.reject(new Error('Canvas failure')), cancel: pdf.cancel }))
    const { error, loaded } = mount()
    await vi.waitFor(() => expect(error).toHaveBeenCalledOnce())
    expect(error.mock.calls[0][0]).toContain('Canvas failure')
    expect(loaded).not.toHaveBeenCalled()
  })

  it('cancels an in-flight render before drawing a replacement document', async () => {
    const oldDrawing = deferred<void>()
    const cancel = vi.fn(() => oldDrawing.reject(new Error('Rendering cancelled')))
    pdf.render.mockImplementationOnce(() => ({ promise: oldDrawing.promise, cancel }))
    const { error, loaded, state } = mount()
    await vi.waitFor(() => expect(pdf.render).toHaveBeenCalledOnce())
    state.src = '/api/papers/2/pdf'
    await vi.waitFor(() => expect(loaded).toHaveBeenCalledOnce())
    expect(cancel).toHaveBeenCalled()
    expect(pdf.render).toHaveBeenCalledTimes(2)
    expect(error).not.toHaveBeenCalled()
  })

  it('ignores a stale document response and disposes workers on replacement/unmount', async () => {
    const old = deferred<ReturnType<typeof makeDocument>>()
    const oldDestroy = vi.fn(async () => {})
    const newDestroy = vi.fn(async () => {})
    pdf.getDocument.mockImplementationOnce(() => ({ promise: old.promise, destroy: oldDestroy }))
      .mockImplementationOnce(() => ({ promise: Promise.resolve(makeDocument()), destroy: newDestroy }))
    const { loaded, error, state } = mount()
    await vi.waitFor(() => expect(pdf.getDocument).toHaveBeenCalledOnce())
    state.src = '/api/papers/2/pdf'
    await vi.waitFor(() => expect(loaded).toHaveBeenCalledOnce())
    expect(oldDestroy).toHaveBeenCalledOnce()
    old.reject(new Error('obsolete request'))
    await nextTick()
    expect(error).not.toHaveBeenCalled()
    app!.unmount()
    app = undefined
    expect(newDestroy).toHaveBeenCalledOnce()
  })
})
