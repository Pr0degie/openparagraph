// Graph renderer. ONE Three.js renderer (3d-force-graph) serves all three views;
// the view is chosen by URL hash and only swaps the z-coordinate source + camera:
//   #mode=2d    → z=0, flat FA2 map, rotation locked (the familiar 2D map)
//   #mode=2.5d  → FA2 x/y map + semantic z (pipeline PCA z when present, else main_group)
//   #mode=3d    → full in-browser 3D force layout
// See docs/decisions/009-single-renderer-3d.md.
import './style.css'
import ForceGraph3D from '3d-force-graph'
import * as THREE from 'three'
import { loadNodes, loadEdges } from './data'
import type { GraphNode } from './types'

// --- sigma-like flat node look: crisp MeshBasic fill (ignores light, no dim
// gradient) + thin dark BackSide outline as a border ring. Geometry/materials
// cached so 6124 nodes stay cheap.
const geoCache = new Map<string, any>()
function sphereGeo(r: number): any {
  const key = r.toFixed(1)
  let g = geoCache.get(key)
  if (!g) {
    g = new THREE.SphereGeometry(r, 10, 10)
    geoCache.set(key, g)
  }
  return g
}
const fillMatCache = new Map<string, any>()
function fillMat(color: string): any {
  let m = fillMatCache.get(color)
  if (!m) {
    m = new THREE.MeshBasicMaterial({ color })
    fillMatCache.set(color, m)
  }
  return m
}
const outlineMat = new THREE.MeshBasicMaterial({ color: 0x0b0b0d, side: THREE.BackSide })

// Node radius factor. Lower = smaller dots = less overlap in the flat 2D view
// (where overlapping nodes fully occlude each other). 2.0 clumped hard; 1.2
// keeps a little overlap in the dense core but lets you tell nodes apart.
const NODE_R = 1.2

function makeNodeObject(node: any): any {
  const r = Math.cbrt(node.val || 1) * NODE_R
  const fill = new THREE.Mesh(sphereGeo(r), fillMat(node.color))
  const outline = new THREE.Mesh(sphereGeo(+(r * 1.28).toFixed(1)), outlineMat)
  const group = new THREE.Group()
  group.add(outline, fill)
  return group
}

const POS_SCALE = 20 // FA2 coords are ±~20000 → bring into a camera-friendly range
const Z_STEP = 100 // vertical gap per FNA main_group level in 2.5D mode

type Mode = '2d' | '2.5d' | '3d'
function currentMode(): Mode {
  const raw = location.hash.match(/mode=([^&]+)/)?.[1] ?? ''
  if (raw === '2d') return '2d'
  if (raw === '3d' || raw === 'force') return '3d'
  return '2.5d'
}

// z-band from the FNA main group (1–9). Centered on 5, null → mid plane.
function zFromMainGroup(node: GraphNode): number {
  const g = node.classification?.main_group
  if (g == null) return 0
  return (g - 5) * Z_STEP
}

const LABELS: Record<Mode, string> = {
  '2d': '2D (flache FA2-Karte)',
  '2.5d': '2.5D (FA2-Karte + z)',
  '3d': 'echtes 3D (d3-force)',
}
const MODES: Mode[] = ['2d', '2.5d', '3d']

function banner(mode: Mode): void {
  const link = (m: Mode) =>
    m === mode
      ? `<b style="color:#fff">${m}</b>`
      : `<a style="color:#6db3ff" href="#mode=${m}">${m}</a>`
  const el = document.createElement('div')
  el.style.cssText =
    'position:fixed;top:8px;left:8px;z-index:10;font:13px system-ui;' +
    'color:#c8c8c8;background:#1a1a1ecc;padding:6px 10px;border-radius:6px'
  el.innerHTML =
    `Ansicht: <b>${LABELS[mode]}</b> &nbsp;·&nbsp; ${MODES.map(link).join(' / ')}`
  document.body.appendChild(el)
}

// Selecting a mode only changes the URL hash, which alone won't re-render.
// Reload so the new mode is built from scratch.
window.addEventListener('hashchange', () => location.reload())

async function main(): Promise<void> {
  const container = document.getElementById('app')!
  const mode = currentMode()
  banner(mode)

  let nodes, edges
  try {
    ;[nodes, edges] = await Promise.all([loadNodes(), loadEdges()])
  } catch (err) {
    container.id = 'error'
    container.textContent =
      `Could not load graph data.\n\n${String(err)}\n\n` +
      'Run the pipeline first, or place fixture JSON in web/public/data/.'
    return
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
      // Seed from the FA2 layout (+ small z jitter) so the 3D relaxation starts
      // near a good solution and is on-screen immediately.
      base.x = n.x / POS_SCALE
      base.y = n.y / POS_SCALE
      base.z = ((n.id.charCodeAt(0) % 11) - 5) * 20
    } else {
      // 2d / 2.5d: fix every node so the force engine never moves it.
      base.fx = n.x / POS_SCALE
      base.fy = n.y / POS_SCALE
      // 2.5d z: prefer the pipeline's semantic z (PCA, same coord space as x/y)
      // once it exists; until then fall back to the FNA main_group band.
      base.fz = mode === '2.5d' ? (n.z != null ? n.z / POS_SCALE : zFromMainGroup(n)) : 0
    }
    return base
  })

  const gLinks = edges
    .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
    .map((e) => ({ source: e.source, target: e.target }))

  const Graph = new (ForceGraph3D as any)(container)
    .backgroundColor('#0d0d0f')
    .graphData({ nodes: gNodes, links: gLinks })
    .nodeId('id')
    .nodeLabel('label')
    .nodeThreeObject(makeNodeObject)
    .linkColor(() => '#3a3a3a')
    .linkOpacity(0.12)
    .linkWidth(0)
    .enableNodeDrag(false)
    .onNodeClick((node: any) => {
      // fly camera to the clicked node (proves Stufe-4 fly-to is trivial here)
      const dist = 120
      const ratio = 1 + dist / Math.hypot(node.x || 1, node.y || 1, node.z || 1)
      Graph.cameraPosition(
        { x: (node.x || 0) * ratio, y: (node.y || 0) * ratio, z: (node.z || 0) * ratio },
        node,
        1500,
      )
    })

  const fixed = mode !== '3d'
  Graph.cooldownTicks(fixed ? 0 : 80) // fixed coords → no sim; 3d → settle fast

  // In 2D: look straight DOWN onto the map. The FA2 cloud is NOT centred on the
  // origin, so the camera must sit directly above the cloud's centre — otherwise
  // zoomToFit pulls it along a slanted axis and the view tilts. Rotation locked.
  if (mode === '2d') {
    const controls: any = Graph.controls()
    controls.noRotate = true
    const xs = gNodes.map((n) => n.fx as number)
    const ys = gNodes.map((n) => n.fy as number)
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2
    const cy = (Math.min(...ys) + Math.max(...ys)) / 2
    setTimeout(() => Graph.cameraPosition({ x: cx, y: cy, z: 2200 }, { x: cx, y: cy, z: 0 }, 0), 250)
    // fit AFTER the camera sits straight above centre → stays perfectly top-down
    setTimeout(() => Graph.zoomToFit(600, 60), 350)
    return
  }

  // Fit the whole corpus in view. Fixed modes are instant; 3D refits while settling.
  const fit = () => Graph.zoomToFit(600, 40)
  setTimeout(fit, 300)
  if (mode === '3d') {
    setTimeout(fit, 1500)
    setTimeout(fit, 3500)
    Graph.onEngineStop(fit)
  }
}

main()
