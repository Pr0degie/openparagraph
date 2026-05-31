import { DirectedGraph } from 'graphology'
import type { GraphNode, GraphEdge } from './types'

export function buildGraph(nodes: GraphNode[], edges: GraphEdge[]): DirectedGraph {
  const graph = new DirectedGraph()

  for (const node of nodes) {
    graph.addNode(node.id, {
      x: node.x,
      y: node.y,
      size: node.size * 0.45,
      color: node.color,
      label: node.jurabk ?? node.id,
    })
  }

  const nodeSet = new Set(graph.nodes())
  for (const edge of edges) {
    if (!nodeSet.has(edge.source) || !nodeSet.has(edge.target)) continue
    if (!graph.hasDirectedEdge(edge.source, edge.target)) {
      graph.addDirectedEdge(edge.source, edge.target, { weight: edge.weight })
    }
  }

  return graph
}
