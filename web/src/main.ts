// Graph renderer. ONE Three.js renderer (3d-force-graph) serves all three views;
// the view is chosen by URL hash and only swaps the z-coordinate source + camera:
//   #mode=2d    → z=0, flat FA2 map, rotation locked
//   #mode=2.5d  → FA2 x/y map + discrete z layers (one plane per FNA main_group)
//   #mode=3d    → full in-browser 3D force layout
// See docs/decisions/009-single-renderer-3d.md.
import './style.css'
import ForceGraph3D from '3d-force-graph'
import * as THREE from 'three'
import { loadNodes, loadEdges } from './data'
import { parseYear, isInTimeWindow } from './timefilter'
import type { GraphNode, GraphEdge } from './types'
import {
  initTooltip, showTooltip, hideTooltip,
  initPanel, showPanel,
  initSearch, initTimeSlider, initTunePanel, initBanner,
  type Mode,
} from './ui'

// ── Constants ──────────────────────────────────────────────────────────────────
const NODE_R = 1.4     // base radius multiplier
const POS_SCALE = 20   // FA2 coords ±~20000 → camera-friendly range

// ── Live-tunable visual params (driven by the tuning panel) ──────────────────────
let tuneLayerGap = 100       // 2.5D: z-distance between FNA main_group planes
let tuneSpread = 1           // x/y spread multiplier (node distance in the plane)
let tuneLargeMul = 1         // size × for "large" nodes (those with a permanent label)
let tuneSmallMul = 1         // size × for all other nodes
let tuneLabelThreshold = 7.5 // node.size ≥ this ⇒ "large" ⇒ permanent label
let tuneLabelGap = 3.5       // vertical gap from the (scaled) sphere top to its label
let tuneGravity = 0.18       // 3D: pull of every node toward the centre (0 = none)
let tuneRepel = 12           // 3D: node-node repulsion strength (d3 charge ≈ 30 default)
let tuneRingRadius = 400     // 3D: radius of the Saturn ring of unclassified laws
let tuneRingWidth = 60       // 3D: radial band thickness of the ring
let tuneRingZJitter = 20     // 3D: out-of-plane thickness of the ring (before tilt)
let tuneRingTilt = 0.35      // 3D: ring tilt about the x-axis, radians (0 = flat z-plane)
let tuneRingDim = 0.5        // 3D: size/colour de-emphasis of ring nodes (1 = none)

// ── Saturn ring (3D) ─────────────────────────────────────────────────────────
// The ~46% of laws with no FNA classification carry no meaningful map position,
// so in 3D we pull them out of the force cloud and pin them to a thin flat ring
// around it — letting the classified clusters in the centre read clearly.
const isUnclassified = (n: GraphNode): boolean => n.classification?.main_group == null
const GOLDEN = Math.PI * (3 - Math.sqrt(5))   // ≈ 2.39996 rad — even angular spread

// Stable index of every ring node (built once in main, in node array order).
let ringIndex = new Map<string, number>()

// Deterministic position of ring node #i on a thin, tilted annulus. Golden-angle
// for the angle; decorrelated fractional sequences for radius/z so the band reads
// as a thin ring (not a 1-node-wide wire or a spiral).
function ringPos(i: number): { fx: number; fy: number; fz: number } {
  const theta = i * GOLDEN
  const radius = tuneRingRadius + ((i * 0.61803398875) % 1 - 0.5) * tuneRingWidth
  const zJit = ((i * 0.7548776662467) % 1 - 0.5) * tuneRingZJitter
  const rx = Math.cos(theta) * radius
  const ry = Math.sin(theta) * radius
  return {
    fx: rx,
    fy: ry * Math.cos(tuneRingTilt) - zJit * Math.sin(tuneRingTilt),
    fz: ry * Math.sin(tuneRingTilt) + zJit * Math.cos(tuneRingTilt),
  }
}

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

// Per-node Three.js parts, tracked so the tuning panel can rescale spheres and
// toggle label visibility live without rebuilding the whole scene.
interface NodeParts {
  id: string
  group: THREE.Group
  fill: THREE.Mesh
  outline: THREE.Mesh
  label: THREE.Sprite
  baseR: number
  size: number
  isRing: boolean
}
const nodeParts = new Map<string, NodeParts>()
let hoveredId: string | null = null

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
  // depthTest:true → a closer opaque sphere occludes labels of nodes behind it
  // (otherwise you'd read the rear node's text through the front sphere).
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: true })
  const sprite = new THREE.Sprite(mat)
  sprite.scale.set(14, 4, 1)
  return sprite
}

// ── Node object factory ────────────────────────────────────────────────────────
function makeNodeObject(node: any): THREE.Group {
  const id = node.id as string
  const size = (node.val as number) || 1
  const baseR = Math.max(Math.cbrt(size) * NODE_R, 0.6)
  const mat = new THREE.MeshBasicMaterial({ color: node.color as string })
  nodeFillMats.set(id, mat)

  const fill = new THREE.Mesh(sphereGeo(baseR), mat)
  const outline = new THREE.Mesh(sphereGeo(+(baseR * 1.3).toFixed(1)), outlineMat)

  // Label sprite: sizeAttenuation=true (default) → readable when zoomed in,
  // tiny/invisible when zoomed out — no per-frame JS needed.
  const label = makeLabel(node.label as string)

  const group = new THREE.Group()
  group.add(outline, fill, label)

  const parts: NodeParts = { id, group, fill, outline, label, baseR, size, isRing: ringIndex.has(id) }
  nodeParts.set(id, parts)
  applyNodeSize(parts)   // sets scale, label offset + visibility from tune state
  return group
}

// Apply the current size/label tune state to one node's parts.
function applyNodeSize(p: NodeParts): void {
  const isLarge = p.size >= tuneLabelThreshold
  // Ring (unclassified) nodes are shrunk so the central clusters dominate.
  const mul = (isLarge ? tuneLargeMul : tuneSmallMul) * (p.isRing ? tuneRingDim : 1)
  p.fill.scale.setScalar(mul)
  p.outline.scale.setScalar(mul)
  // Float the label above the scaled outline so the node never hides its own label.
  p.label.position.y = p.baseR * 1.3 * mul + tuneLabelGap
  // Large nodes always labelled; the rest only while hovered.
  p.label.visible = isLarge || p.id === hoveredId
}

function applyAllSizes(): void {
  nodeParts.forEach(applyNodeSize)
}

// ── Highlight + time filter ────────────────────────────────────────────────────
let searchActive = false
const highlightedIds = new Set<string>()

let timeFilterActive = false
let timeRange: [number, number] = [0, 9999]

function applyHighlight(nodeById: Map<string, GraphNode>): void {
  nodeFillMats.forEach((mat, id) => {
    const n = nodeById.get(id)
    if (!n) return
    const inSearch = !searchActive || highlightedIds.has(id)
    // Interval-overlap: a law is shown if its lifespan [born, death] intersects
    // the slider window. death = repealed_at (null = still in force).
    const inTime = !timeFilterActive || isInTimeWindow(
      parseYear(n.created_at),
      parseYear(n.repealed_at),
      timeRange[0],
      timeRange[1],
    )
    if (inSearch && inTime) {
      // Ring (unclassified) nodes are muted by default so the classified clusters
      // pop; an active search match still gets full colour so it stays findable.
      const muteRing = ringIndex.has(id) && tuneRingDim < 1 && !(searchActive && highlightedIds.has(id))
      mat.color.set(muteRing ? '#3a3a44' : n.color)
      mat.opacity = 1
      mat.transparent = false
    } else {
      // De-emphasise via a solid dark colour — never transparent (spheres must
      // stay opaque so you can't see through them). See feedback memory.
      mat.color.set('#23232b')
      mat.opacity = 1
      mat.transparent = false
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
  return g != null ? (g - 5) * tuneLayerGap : 0
}

// A custom d3-force that pulls every node toward the origin (centre gravity).
// Hand-rolled to avoid pulling in d3-force-3d just for forceRadial.
function centerGravityForce() {
  let nodes: any[] = []
  let strength = 0.1
  const force = (alpha: number) => {
    for (const n of nodes) {
      n.vx -= n.x * strength * alpha
      n.vy -= n.y * strength * alpha
      n.vz -= (n.z || 0) * strength * alpha
    }
  }
  force.initialize = (n: any[]) => { nodes = n }
  force.strength = (s: number) => { strength = s; return force }
  return force
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

  // Build the stable ring index (node array order) before gNodes so the 3D map
  // can pin unclassified nodes and makeNodeObject can flag them.
  ringIndex = new Map(nodes.filter(isUnclassified).map((n, i) => [n.id, i]))

  const gNodes = nodes.map((n) => {
    const base: Record<string, unknown> = {
      id: n.id,
      label: n.jurabk ?? n.id,
      color: n.color,
      val: n.size,
    }
    if (mode === '3d') {
      if (isUnclassified(n)) {
        // Pin to the Saturn ring; classified nodes stay free-floating below.
        const { fx, fy, fz } = ringPos(ringIndex.get(n.id)!)
        base.fx = fx; base.fy = fy; base.fz = fz
      } else {
        base.x = n.x / POS_SCALE
        base.y = n.y / POS_SCALE
        base.z = ((n.id.charCodeAt(0) % 11) - 5) * 20
      }
    } else {
      base.fx = (n.x / POS_SCALE) * tuneSpread
      base.fy = (n.y / POS_SCALE) * tuneSpread
      base.fz = mode === '2.5d' ? zFromMainGroup(n) : 0
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
      // Toggle the on-hover label for small nodes (large nodes are always labelled).
      const newId = node ? (node.id as string) : null
      if (newId !== hoveredId) {
        if (hoveredId) {
          const p = nodeParts.get(hoveredId)
          if (p) p.label.visible = p.size >= tuneLabelThreshold
        }
        hoveredId = newId
        if (hoveredId) {
          const p = nodeParts.get(hoveredId)
          if (p) p.label.visible = true
        }
      }
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

  // ── 3D force tuning ─────────────────────────────────────────────────────────
  // Only meaningful in 3D (2d/2.5d are statically pinned). Pull nodes toward the
  // centre and soften the default repulsion so the cloud stays compact.
  const gravityForce = centerGravityForce().strength(tuneGravity)
  if (mode === '3d') {
    // Register the custom forces on the (already-created) d3 simulation. Do NOT
    // call d3ReheatSimulation() here: it synchronously sets engineRunning=true and
    // starts the tick loop, but `state.layout` is only assigned at the end of the
    // deferred graphData digest (next animation frame). The race crashed layoutTick
    // with "Cannot read properties of undefined (reading 'tick')" → black screen.
    // The engine starts itself after the digest and picks up these forces.
    Graph.d3Force('charge').strength(-tuneRepel)
    Graph.d3Force('gravity', gravityForce)
  }

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

  // ── Tuning panel wiring ─────────────────────────────────────────────────────
  // Recompute fixed node positions in place (no scene rebuild). Position-only
  // changes work because 2d/2.5d are static (cooldownTicks=0); 3d is left alone.
  function applyPositions(): void {
    if (mode === '3d') return
    nodeParts.forEach((p, id) => {
      const n = nodeById.get(id)
      if (!n) return
      const fx = (n.x / POS_SCALE) * tuneSpread
      const fy = (n.y / POS_SCALE) * tuneSpread
      const fz = mode === '2.5d' ? zFromMainGroup(n) : 0
      p.group.position.set(fx, fy, fz)
      const g = gNodeById.get(id)
      if (g) {
        g.fx = fx; g.fy = fy; g.fz = fz            // pin to the new fixed coords
        g.x = fx; g.y = fy; g.z = fz               // and the live coords the lib reads
      }
    })
    // The lib only rewrites object positions inside layoutTick, which stops once
    // the engine cools (cooldownTicks=0). Reheat for one tick so the new fixed
    // coords are applied; all nodes are pinned, so nothing drifts.
    Graph.d3ReheatSimulation()
  }

  // Recompute the pinned ring coords in place (3D only) when a ring slider moves.
  // Mirrors applyPositions: rewrite fixed + live coords, nudge the Three group,
  // then reheat one tick so the lib flushes the new positions (ring nodes are
  // pinned, so nothing drifts; the free cloud re-settles in the same basin).
  function applyRing(): void {
    if (mode !== '3d') return
    ringIndex.forEach((i, id) => {
      const { fx, fy, fz } = ringPos(i)
      const g = gNodeById.get(id)
      if (g) { g.fx = fx; g.fy = fy; g.fz = fz; g.x = fx; g.y = fy; g.z = fz }
      const p = nodeParts.get(id)
      if (p) p.group.position.set(fx, fy, fz)
    })
    Graph.d3ReheatSimulation()
  }

  const tuneSpecs = [
    { key: 'largeSize', label: 'Große Kugeln ×', min: 0.5, max: 6, step: 0.1, value: tuneLargeMul },
    { key: 'smallSize', label: 'Andere Kugeln ×', min: 0.2, max: 4, step: 0.1, value: tuneSmallMul },
    { key: 'labelThreshold', label: 'Label-Schwelle', min: 2, max: 30, step: 0.5, value: tuneLabelThreshold },
    { key: 'labelGap', label: 'Label-Abstand', min: 0, max: 20, step: 0.5, value: tuneLabelGap },
  ]
  if (mode === '2.5d') {
    tuneSpecs.unshift({ key: 'layerGap', label: 'Ebenen-Abstand', min: 0, max: 600, step: 10, value: tuneLayerGap })
  }
  if (mode !== '3d') {
    tuneSpecs.unshift({ key: 'spread', label: 'Knoten-Abstand', min: 0.3, max: 3, step: 0.05, value: tuneSpread })
  } else {
    tuneSpecs.push(
      { key: 'gravity', label: 'Zentrum-Anziehung', min: 0, max: 1, step: 0.02, value: tuneGravity },
      { key: 'repel', label: 'Abstoßung', min: 0, max: 60, step: 1, value: tuneRepel },
      { key: 'ringRadius', label: 'Ring-Radius', min: 150, max: 900, step: 10, value: tuneRingRadius },
      { key: 'ringWidth', label: 'Ring-Breite', min: 0, max: 300, step: 5, value: tuneRingWidth },
      { key: 'ringZJitter', label: 'Ring-Dicke', min: 0, max: 120, step: 2, value: tuneRingZJitter },
      { key: 'ringTilt', label: 'Ring-Neigung', min: 0, max: 1.2, step: 0.02, value: tuneRingTilt },
      { key: 'ringDim', label: 'Ring-Dämpfung', min: 0.2, max: 1, step: 0.05, value: tuneRingDim },
    )
  }

  initTunePanel(tuneSpecs, (key, v) => {
    switch (key) {
      case 'layerGap': tuneLayerGap = v; applyPositions(); break
      case 'spread': tuneSpread = v; applyPositions(); break
      case 'largeSize': tuneLargeMul = v; applyAllSizes(); break
      case 'smallSize': tuneSmallMul = v; applyAllSizes(); break
      case 'labelThreshold': tuneLabelThreshold = v; applyAllSizes(); break
      case 'labelGap': tuneLabelGap = v; applyAllSizes(); break
      case 'gravity': tuneGravity = v; gravityForce.strength(v); Graph.d3ReheatSimulation(); break
      case 'repel': tuneRepel = v; Graph.d3Force('charge').strength(-v); Graph.d3ReheatSimulation(); break
      case 'ringRadius': tuneRingRadius = v; applyRing(); break
      case 'ringWidth': tuneRingWidth = v; applyRing(); break
      case 'ringZJitter': tuneRingZJitter = v; applyRing(); break
      case 'ringTilt': tuneRingTilt = v; applyRing(); break
      case 'ringDim': tuneRingDim = v; applyAllSizes(); applyHighlight(nodeById); break
    }
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

  // In 3D, fit the camera to the classified cluster cloud only (exclude the ring
  // via getGraphBbox's node-filter arg) so the clusters fill the view and the ring
  // frames them. 2.5D has no ring, so fit everything.
  const fit = mode === '3d'
    ? () => Graph.zoomToFit(600, 40, (node: any) => !ringIndex.has(node.id as string))
    : () => Graph.zoomToFit(600, 40)
  setTimeout(fit, 300)
  if (mode === '3d') {
    setTimeout(fit, 1500)
    setTimeout(fit, 3500)
    Graph.onEngineStop(fit)
  }
}

main()
