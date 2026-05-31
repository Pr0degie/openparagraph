export interface Classification {
  scheme: 'FNA'
  code: string | null
  main_group: number | null
}

export interface GraphNode {
  id: string
  jurisdiction: string
  jurabk: string | null
  title: string | null
  classification: Classification
  meta_cluster: string | null
  created_at: string | null
  repealed_at: string | null
  x: number
  y: number
  color: string
  size: number
  degree: number
}

export interface GraphEdge {
  source: string
  target: string
  type: string
  weight: number
}
