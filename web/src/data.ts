import type { GraphNode, GraphEdge } from './types'

export async function loadNodes(jurisdiction = 'de-bund'): Promise<GraphNode[]> {
  const res = await fetch(`/data/${jurisdiction}/nodes.json`)
  if (!res.ok) throw new Error(`nodes.json: HTTP ${res.status}`)
  return res.json() as Promise<GraphNode[]>
}

export async function loadEdges(): Promise<GraphEdge[]> {
  const res = await fetch('/data/_global/edges.json')
  if (!res.ok) throw new Error(`edges.json: HTTP ${res.status}`)
  return res.json() as Promise<GraphEdge[]>
}
