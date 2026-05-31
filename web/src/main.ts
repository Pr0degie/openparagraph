// Graph renderer. ONE Three.js renderer (3d-force-graph) serves all three views;
// the view is chosen by URL hash and only swaps the z-coordinate source + camera:
//   #mode=2d    → z=0, flat FA2 map, rotation locked
//   #mode=2.5d  → FA2 x/y map + semantic z (pipeline PCA z)
//   #mode=3d    → full in-browser 3D force layout
// See docs/decisions/009-single-renderer-3d.md.
import './style.css'
import ForceGraph3D from '3d-force-graph'
import * as THREE from 'three'
import { loadNodes, loadEdges } from './data'
import type { GraphNode, GraphEdge } from './types'
import {
  initTooltip, showTooltip, hideTooltip,
  initPanel, showPanel,
  initSearch, initTimeSlider, initBanner,
  type Mode,
} from './ui'

// ── Constants ──────────────────────────────────────────────────────────────────
const NODE_R = 1.4     // base radius multiplier
const POS_SCALE = 20   // FA2 coords ±~20000 → camera-friendly range
const Z_STEP = 100     // z-band per FNA main_group in fallback 2.5D mode

// ── Mode ───────────────────────────────────────────────────────────────────────
function currentMode(): Mode {
  const raw = location.hash.match(/mode=([^&]+)/)?.[1] ?? ''
  if (raw === '2d') return '2d'
  if (raw === '3d' || raw === 'force') return '3d'
  return '2.5d'
}

window.addEventListener('hashchange', () => location.reload())

// ── Geometry / material cache ──────────────────────────────────────────────────
const geoCache = new Map<string, THREE.SphereGeometry>()
function sphereGeo(r: number): THREE.SphereGeometry {
  const key = r.toFixed(1)
  let g = geoCache.get(key)
  if (!g) {
    g = new THREE.SphereGeometry(r, 12, 12)
    geoCache.set(key, g)
  }
  return g
}

const outlineMat = new THREE.MeshBasicMaterial({ color: 0x0a0a0d, side: THREE.BackSide })

// Each node's fill material is tracked so highlight can recolour them imperatively.
const nodeFillMats = new Map<string, THREE.MeshBasicMaterial>()

// ── Node labels ────────────────────────────────────────────────────────────────
// OffscreenCanvas avoids DOM overhead; falls back to regular canvas.
function makeLabel(text: string): THREE.Sprite {
  const W = 256, H = 44
  const canvas: HTMLCanvasElement =
    typeof OffscreenCanvas !== 'undefined'
      ? (new OffscreenCanvas(W, H) as unknown as HTMLCanvasElement)
      : Object.assign(document.createElement('canvas'), { width: W, height: H })
  const ctx = canvas.getContext('2d') as CanvasRenderingContext2D
  const label = text.length > 14 ? `${text.slice(0, 13)}…` : text
  ctx.font = 'bold 18px system-ui, sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = 'rgba(255,255,255,0.88)'
  ctx.fillText(label, W / 2, H / 2)
  const tex = new THREE.CanvasTexture(canvas)
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false })
  const sprite = new THREE.Sprite(mat)
  sprite.scale.set(14, 4, 1)
  return sprite
}

// ── Node object factory ────────────────────────────────────────────────────────
function makeNodeObject(node: any): THREE.Group {
  const r = Math.max(Math.cbrt((node.val as number) || 1) * NODE_R, 0.6)
  const mat = new THREE.MeshBasicMaterial({ color: node.color as string })
  nodeFillMats.set(node.id as string, mat)

  const fill = new THREE.Mesh(sphereGeo(r), mat)
  const outline = new THREE.Mesh(sphereGeo(+(r * 1.3).toFixed(1)), outlineMat)

  // Label sprite: sizeAttenuation=true (default) → readable when zoomed in,
  // tiny/invisible when zoomed out — no per-frame JS needed.
  const label = makeLabel(node.label as string)
  label.position.y = r + 3.5

  const group = new THREE.Group()
  group.add(outline, fill, label)
  return group
}

// ── Highlight + time filter ────────────────────────────────────────────────────
let searchActive = false
const highlightedIds = new Set<string>()

let timeFilterActive = false
let timeRange: [number, number] = [0, 9999]

function parseYear(date: string | null): number | null {
  if (!date || date.startsWith('0000')) return null
  const y = parseInt(date.slice(0, 4), 10)
  return isNaN(y) ? null : y
}

function applyHighlight(nodeById: Map<string, GraphNode>): void {
  nodeFillMats.forEach((mat, id) => {
    const n = nodeById.get(id)
    if (!n) return
    const inSearch = !searchActive || highlightedIds.has(id)
    const inTime = !timeFilterActive || (() => {
      const y = parseYear(n.created_at)
      return y == null || (y >= timeRange[0] && y <= timeRange[1])
    })()
    if (inSearch && inTime) {
      mat.color.set(n.color)
      mat.opacity = 1
      mat.transparent = false
    } else {
      mat.color.set('#1a1a22')
      mat.opacity = 0.22
      mat.transparent = true
    }
  })
}

// Simple substring search (6124 nodes × short strings ≈ 2-4 ms — no FlexSearch needed).
function runSearch(query: string, nodes: GraphNode[]): Set<string> {
  const q = query.trim().toLowerCase()
  if (!q) return new Set()
  const result = new Set<string>()
  for (const n of nodes) {
    if (`${n.jurabk ?? ''} ${n.title ?? ''}`.toLowerCase().includes(q)) {
      result.add(n.id)
    }
  }
  return result
}

// ── z helpers ──────────────────────────────────────────────────────────────────
function zFromMainGroup(node: GraphNode): number {
  const g = node.classification?.main_group
  return g != null ? (g - 5) * Z_STEP : 0
}

// ── Main ───────────────────────────────────────────────────────────────────────
async function main(): Promise<void> {
  const container = document.getElementById('app')!
  const mode = currentMode()

  initBanner(mode)
  initTooltip()
  initPanel()

  let nodes: GraphNode[], edges: GraphEdge[]
  try {
    ;[nodes, edges] = await Promise.all([loadNodes(), loadEdges()])
  } catch (err) {
    container.id = 'error'
    container.textContent =
      `Could not load graph data.\n\n${String(err)}\n\n` +
      'Run the pipeline first, or place fixture JSON in web/public/data/.'
    return
  }

  // Lookup tables
  const nodeById = new Map(nodes.map((n) => [n.id, n]))
  const adjOut = new Map<string, GraphEdge[]>()
  const adjIn = new Map<string, GraphEdge[]>()
  for (const e of edges) {
    if (!adjOut.has(e.source)) adjOut.set(e.source, [])
    if (!adjIn.has(e.target)) adjIn.set(e.target, [])
    adjOut.get(e.source)!.push(e)
    adjIn.get(e.target)!.push(e)
  }

  const nodeIds = new Set(nodes.map((n) => n.id))

  const gNodes = nodes.map((n) => {
    const base: Record<string, unknown> = {
      id: n.id,
      label: n.jurabk ?? n.id,
      color: n.color,
      val: n.size,
    }
    if (mode === '3d') {
      base.x = n.x / POS_SCALE
      base.y = n.y / POS_SCALE
      base.z = ((n.id.charCodeAt(0) % 11) - 5) * 20
    } else {
      base.fx = n.x / POS_SCALE
      base.fy = n.y / POS_SCALE
      base.fz = mode === '2.5d' ? (n.z != null ? n.z / POS_SCALE : zFromMainGroup(n)) : 0
    }
    return base
  })

  const gNodeById = new Map(gNodes.map((n) => [n.id as string, n]))

  const gLinks = edges
    .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
    .map((e) => ({ source: e.source, target: e.target }))

  // Mouse position for tooltip placement (onNodeHover doesn't carry coordinates)
  let mouseX = 0, mouseY = 0
  container.addEventListener('mousemove', (e) => { mouseX = e.clientX; mouseY = e.clientY })

  // Overview position for 2D reset button
  let overview2d = { x: 0, y: 0 }

  function flyTo(id: string): void {
    const gNode = gNodeById.get(id)
    if (!gNode) return
    const x = ((mode === '3d' ? gNode.x : gNode.fx) ?? 0) as number
    const y = ((mode === '3d' ? gNode.y : gNode.fy) ?? 0) as number
    const z = ((mode === '3d' ? gNode.z : gNode.fz) ?? 0) as number

    if (mode === '2d') {
      // 2D detail view: rotate camera 90° to the left (side-on from −x direction).
      const ctrl = Graph.controls() as any
      ctrl.noRotate = false
      Graph.cameraPosition({ x: x - 260, y, z: 90 }, { x, y, z: 0 }, 1200)
    } else {
      const dist = 120
      const len = Math.hypot(x || 0.01, y || 0.01, z || 0.01)
      const ratio = 1 + dist / len
      Graph.cameraPosition(
        { x: x * ratio, y: y * ratio, z: z * ratio + dist * 0.4 },
        { x, y, z },
        1200,
      )
    }

    const nodeData = nodeById.get(id)
    if (nodeData) {
      showPanel(
        nodeData,
        adjOut.get(id) ?? [],
        adjIn.get(id) ?? [],
        nodeById,
        flyTo,
        mode === '2d' ? resetCamera2d : undefined,
      )
    }
  }

  function resetCamera2d(): void {
    const ctrl = Graph.controls() as any
    ctrl.noRotate = true
    Graph.cameraPosition(
      { x: overview2d.x, y: overview2d.y, z: 2200 },
      { x: overview2d.x, y: overview2d.y, z: 0 },
      1000,
    )
  }

  // ── Graph instance ────────────────────────────────────────────────────────────
  const Graph = new (ForceGraph3D as any)(container)
    .backgroundColor('#0d0d0f')
    .graphData({ nodes: gNodes, links: gLinks })
    .nodeId('id')
    .nodeLabel(() => '')          // suppress built-in title; we use custom tooltip
    .nodeThreeObject(makeNodeObject)
    .linkColor(() => '#363640')
    .linkOpacity(0.18)
    .linkWidth(0)
    .enableNodeDrag(false)
    .onNodeHover((node: any) => {
      document.body.style.cursor = node ? 'pointer' : 'default'
      if (node) {
        const n = nodeById.get(node.id as string)
        if (n) showTooltip(n, mouseX, mouseY)
      } else {
        hideTooltip()
      }
    })
    .onNodeClick((node: any) => flyTo(node.id as string))

  // ── Controls ──────────────────────────────────────────────────────────────────
  // three-forcegraph calls controls.update() every frame — enableDamping works.
  const controls = Graph.controls() as any
  controls.enableDamping = true
  controls.dampingFactor = 0.07
  controls.zoomSpeed = 0.35
  controls.rotateSpeed = 0.45
  controls.panSpeed = 0.6

  // ── Search wiring ─────────────────────────────────────────────────────────────
  initSearch((q) => {
    if (!q.trim()) {
      searchActive = false
      highlightedIds.clear()
    } else {
      searchActive = true
      highlightedIds.clear()
      runSearch(q, nodes).forEach((id) => highlightedIds.add(id))
    }
    applyHighlight(nodeById)
  })

  // ── Time slider wiring ────────────────────────────────────────────────────────
  const years = nodes.map((n) => parseYear(n.created_at)).filter((y): y is number => y != null)
  const minYear = Math.min(...years)
  const maxYear = Math.max(...years)
  initTimeSlider(minYear, maxYear, (from, to) => {
    timeFilterActive = from !== minYear || to !== maxYear
    timeRange = [from, to]
    applyHighlight(nodeById)
  })

  // ── Initial camera ────────────────────────────────────────────────────────────
  Graph.cooldownTicks(mode !== '3d' ? 0 : 80)

  if (mode === '2d') {
    controls.noRotate = true
    const xs = gNodes.map((n) => n.fx as number)
    const ys = gNodes.map((n) => n.fy as number)
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2
    const cy = (Math.min(...ys) + Math.max(...ys)) / 2
    overview2d = { x: cx, y: cy }
    setTimeout(() => Graph.cameraPosition({ x: cx, y: cy, z: 2200 }, { x: cx, y: cy, z: 0 }, 0), 250)
    setTimeout(() => Graph.zoomToFit(600, 60), 350)
    return
  }

  const fit = () => Graph.zoomToFit(600, 40)
  setTimeout(fit, 300)
  if (mode === '3d') {
    setTimeout(fit, 1500)
    setTimeout(fit, 3500)
    Graph.onEngineStop(fit)
  }
}

main()
