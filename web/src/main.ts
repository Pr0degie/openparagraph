import './style.css'
import Sigma from 'sigma'
import { loadNodes, loadEdges } from './data'
import { buildGraph } from './graph'

async function main() {
  const container = document.getElementById('app')!

  let nodes, edges
  try {
    ;[nodes, edges] = await Promise.all([loadNodes(), loadEdges()])
  } catch (err) {
    container.id = 'error'
    container.textContent = `Could not load graph data.\n\n${String(err)}\n\nRun the pipeline first, or place fixture JSON in web/public/data/.`
    return
  }

  const graph = buildGraph(nodes, edges)

  new Sigma(graph, container, {
    renderEdgeLabels: false,
    defaultEdgeColor: '#2a2a2a',
    defaultEdgeType: 'arrow',
    labelColor: { color: '#c8c8c8' },
    labelSize: 10,
    minCameraRatio: 0.05,
    maxCameraRatio: 20,
  })
}

main()
