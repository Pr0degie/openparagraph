// UI components: tooltip, detail panel, search box, banner.
// No graph logic here — only DOM manipulation.
import type { GraphNode, GraphEdge } from './types'

export type Mode = '2d' | '2.5d' | '3d'

// ── Tooltip ───────────────────────────────────────────────────────────────────

let _tip: HTMLDivElement

export function initTooltip(): void {
  _tip = document.createElement('div')
  _tip.className = 'op-tooltip'
  document.body.appendChild(_tip)
}

export function showTooltip(node: GraphNode, x: number, y: number): void {
  _tip.innerHTML =
    `<b>${node.jurabk ?? node.id}</b>` +
    (node.title ? `<br>${node.title.replace(/\n/g, ' ').slice(0, 90)}` : '')
  _tip.style.left = `${Math.min(x + 14, window.innerWidth - 290)}px`
  _tip.style.top = `${y - 8}px`
  _tip.style.display = 'block'
}

export function hideTooltip(): void {
  _tip.style.display = 'none'
}

// ── Detail Panel ──────────────────────────────────────────────────────────────

let _panel: HTMLDivElement
let _inner: HTMLDivElement

export function initPanel(): void {
  _panel = document.createElement('div')
  _panel.className = 'op-panel'
  _inner = document.createElement('div')
  _inner.className = 'op-panel-inner'
  _panel.appendChild(_inner)
  document.body.appendChild(_panel)
}

export function showPanel(
  node: GraphNode,
  outEdges: GraphEdge[],
  inEdges: GraphEdge[],
  nodeById: Map<string, GraphNode>,
  onFlyTo: (id: string) => void,
  onReset?: () => void,
): void {
  const chip = (edges: GraphEdge[], keyFn: (e: GraphEdge) => string, total: number) => {
    const html = edges
      .slice(0, 25)
      .map((e) => {
        const n = nodeById.get(keyFn(e))
        return n ? `<a class="op-ref" data-id="${n.id}">${n.jurabk ?? n.id}</a>` : null
      })
      .filter(Boolean)
      .join('')
    const more = total > 25 ? `<span class="op-ref-more">+${total - 25} weitere</span>` : ''
    return html + more
  }

  const outTotal = outEdges.length
  const inTotal = inEdges.length

  _inner.innerHTML = `
    <div class="op-panel-header">
      ${onReset ? `<button class="op-overview-btn">↑ Übersicht</button>` : ''}
      <button class="op-close">✕</button>
    </div>
    <div class="op-jurabk" style="border-left: 4px solid ${node.color}">${node.jurabk ?? node.id}</div>
    <div class="op-title">${(node.title ?? '').replace(/\n/g, ' ')}</div>
    <dl class="op-meta">
      ${node.classification.code ? `<dt>FNA</dt><dd>${node.classification.code}</dd>` : ''}
      ${node.meta_cluster ? `<dt>Cluster</dt><dd>${node.meta_cluster}</dd>` : ''}
      ${node.created_at ? `<dt>In Kraft</dt><dd>${node.created_at}</dd>` : ''}
      ${node.repealed_at ? `<dt>Außer Kraft</dt><dd><span class="op-repealed">${node.repealed_at}</span></dd>` : ''}
      <dt>Verbindungen</dt><dd>${node.degree}</dd>
    </dl>
    ${outTotal ? `<div class="op-section-label">Verweist auf (${outTotal})</div><div class="op-refs">${chip(outEdges, (e) => e.target, outTotal)}</div>` : ''}
    ${inTotal ? `<div class="op-section-label">Zitiert von (${inTotal})</div><div class="op-refs">${chip(inEdges, (e) => e.source, inTotal)}</div>` : ''}
  `

  _inner.querySelectorAll<HTMLElement>('.op-ref[data-id]').forEach((a) => {
    a.addEventListener('click', () => onFlyTo(a.dataset.id!))
  })
  _inner.querySelector('.op-close')?.addEventListener('click', hidePanel)
  _inner.querySelector('.op-overview-btn')?.addEventListener('click', () => {
    hidePanel()
    onReset?.()
  })

  _panel.classList.add('op-panel--open')
}

export function hidePanel(): void {
  _panel?.classList.remove('op-panel--open')
}

// ── Search ────────────────────────────────────────────────────────────────────

export function initSearch(onSearch: (q: string) => void): void {
  const wrap = document.createElement('div')
  wrap.className = 'op-search'
  wrap.innerHTML = '<input type="search" placeholder="Gesetz suchen …" spellcheck="false" autocomplete="off" />'
  document.body.appendChild(wrap)
  const input = wrap.querySelector<HTMLInputElement>('input')!
  input.addEventListener('input', () => onSearch(input.value))
  // Keyboard shortcut: / focuses search
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== input) {
      e.preventDefault()
      input.focus()
    }
    if (e.key === 'Escape') {
      input.value = ''
      onSearch('')
      input.blur()
    }
  })
}

// ── Time slider ───────────────────────────────────────────────────────────────

export function initTimeSlider(
  min: number,
  max: number,
  onChange: (from: number, to: number) => void,
): void {
  const wrap = document.createElement('div')
  wrap.className = 'op-timeslider'
  wrap.innerHTML = `
    <div class="op-timeslider-label">
      <span class="op-ts-from">${min}</span>
      <span class="op-ts-sep"> – </span>
      <span class="op-ts-to">${max}</span>
    </div>
    <div class="op-timeslider-track">
      <input class="op-ts-lo" type="range" min="${min}" max="${max}" value="${min}" step="1" />
      <input class="op-ts-hi" type="range" min="${min}" max="${max}" value="${max}" step="1" />
    </div>
  `
  document.body.appendChild(wrap)

  const lo = wrap.querySelector<HTMLInputElement>('.op-ts-lo')!
  const hi = wrap.querySelector<HTMLInputElement>('.op-ts-hi')!
  const fromLabel = wrap.querySelector<HTMLSpanElement>('.op-ts-from')!
  const toLabel = wrap.querySelector<HTMLSpanElement>('.op-ts-to')!

  function update(): void {
    let f = parseInt(lo.value, 10)
    let t = parseInt(hi.value, 10)
    if (f > t) { [f, t] = [t, f]; lo.value = String(f); hi.value = String(t) }
    fromLabel.textContent = String(f)
    toLabel.textContent = String(t)
    onChange(f, t)
  }

  lo.addEventListener('input', update)
  hi.addEventListener('input', update)
}

// ── Banner ────────────────────────────────────────────────────────────────────

export function initBanner(current: Mode): void {
  const labels: Record<Mode, string> = { '2d': '2D', '2.5d': '2.5D', '3d': '3D' }
  const modes: Mode[] = ['2d', '2.5d', '3d']
  const el = document.createElement('div')
  el.className = 'op-banner'
  const links = modes
    .map((m) =>
      m === current
        ? `<b>${labels[m]}</b>`
        : `<a href="#mode=${m}">${labels[m]}</a>`
    )
    .join('<span class="op-sep"> / </span>')
  el.innerHTML = `<span class="op-logo">openparagraph</span> ${links}`
  document.body.appendChild(el)
}

// ── Tuning panel ──────────────────────────────────────────────────────────────
// A collapsible box of live sliders for visual fine-tuning. Each slider shows
// its current numeric value and fires onChange(key, value) on every input.

export interface TuneSpec {
  key: string
  label: string
  min: number
  max: number
  step: number
  value: number
}

export function initTunePanel(
  specs: TuneSpec[],
  onChange: (key: string, value: number) => void,
): void {
  const wrap = document.createElement('div')
  wrap.className = 'op-tune'
  const rows = specs
    .map(
      (s) => `
      <label class="op-tune-row" data-key="${s.key}">
        <span class="op-tune-label">${s.label}</span>
        <input type="range" min="${s.min}" max="${s.max}" step="${s.step}" value="${s.value}" />
        <span class="op-tune-val">${s.value}</span>
      </label>`,
    )
    .join('')
  wrap.innerHTML = `
    <div class="op-tune-head">Tuning <span class="op-tune-toggle">–</span></div>
    <div class="op-tune-body">${rows}</div>
  `
  document.body.appendChild(wrap)

  const body = wrap.querySelector<HTMLDivElement>('.op-tune-body')!
  const toggle = wrap.querySelector<HTMLSpanElement>('.op-tune-toggle')!
  wrap.querySelector<HTMLDivElement>('.op-tune-head')!.addEventListener('click', () => {
    const hidden = body.style.display === 'none'
    body.style.display = hidden ? '' : 'none'
    toggle.textContent = hidden ? '–' : '+'
  })

  wrap.querySelectorAll<HTMLElement>('.op-tune-row').forEach((row) => {
    const key = row.dataset.key!
    const input = row.querySelector<HTMLInputElement>('input')!
    const val = row.querySelector<HTMLSpanElement>('.op-tune-val')!
    input.addEventListener('input', () => {
      val.textContent = input.value
      onChange(key, parseFloat(input.value))
    })
  })
}
