import { useMemo, useState } from 'react'
import { Html, Line } from '@react-three/drei'
import { hexToRgb } from '../utils/regions.js'

// Edges are drawn in strength bands: stronger connections are thicker and more opaque.
// (WebGL can't vary line width per line, so each band is drawn as one batch.)
const EDGE_BANDS = [
  { minWeight: -1, width: 0.6, opacity: 0.18 },
  { minWeight: 0.4, width: 1.1, opacity: 0.3 },
  { minWeight: 0.55, width: 1.8, opacity: 0.5 },
  { minWeight: 0.7, width: 2.8, opacity: 0.8 },
]
const BASE_NODE_RADIUS = 2.2 // mm

// Work out each node's sphere radius from the chosen statistic.
// Inputs: nodes, sizeBy ("uniform" or a stat key). Output: Map node id -> radius in mm.
function nodeRadii(nodes, sizeBy) {
  const radii = new Map()
  if (sizeBy === 'uniform') {
    nodes.forEach((node) => radii.set(node.id, BASE_NODE_RADIUS))
    return radii
  }
  const largest = Math.max(...nodes.map((node) => node.stats[sizeBy])) || 1
  nodes.forEach((node) => {
    radii.set(node.id, 1.2 + 3.2 * Math.sqrt(node.stats[sizeBy] / largest))
  })
  return radii
}

// Split the visible edges into strength bands, as line-segment point and color lists.
// Inputs: edges to draw, nodesById, networkRgb (network -> [r,g,b]).
// Output: array of { band, points, colors } (empty bands left out).
function edgeBatches(edges, nodesById, networkRgb) {
  const batches = EDGE_BANDS.map((band) => ({ band, points: [], colors: [] }))
  for (const edge of edges) {
    let bandIndex = 0
    EDGE_BANDS.forEach((band, index) => {
      if (edge.weight >= band.minWeight) bandIndex = index
    })
    const source = nodesById.get(edge.source)
    const target = nodesById.get(edge.target)
    const batch = batches[bandIndex]
    batch.points.push([source.x, source.y, source.z], [target.x, target.y, target.z])
    batch.colors.push(networkRgb[source.network], networkRgb[target.network]) // fades between the two networks
  }
  return batches.filter((batch) => batch.points.length > 0)
}

// Nodes (spheres colored by network) and edges (lines weighted by strength).
// Inputs: visibleNodes, visibleEdges, nodesById, networkColors, selectedId,
//         highlightedIds (selected region + its shown partners), sizeBy, onNodeClick(id).
// Output: a group of three.js objects.
export default function NetworkLayer({
  visibleNodes, visibleEdges, nodesById, networkColors, selectedId, highlightedIds, sizeBy, onNodeClick,
}) {
  const [hoveredId, setHoveredId] = useState(null)
  const networkRgb = useMemo(
    () => Object.fromEntries(Object.entries(networkColors).map(([network, hex]) => [network, hexToRgb(hex)])),
    [networkColors],
  )
  const radii = useMemo(() => nodeRadii(visibleNodes, sizeBy), [visibleNodes, sizeBy])
  const batches = useMemo(
    () => edgeBatches(visibleEdges, nodesById, networkRgb),
    [visibleEdges, nodesById, networkRgb],
  )
  const hoveredNode = hoveredId != null ? nodesById.get(hoveredId) : null

  return (
    <group>
      {batches.map(({ band, points, colors }) => (
        <Line
          key={`${band.minWeight}-${points.length}`}
          points={points}
          vertexColors={colors}
          segments
          lineWidth={band.width}
          transparent
          opacity={selectedId != null ? Math.min(1, band.opacity + 0.3) : band.opacity}
          depthWrite={false}
          renderOrder={1}
        />
      ))}

      {visibleNodes.map((node) => {
        const isSelected = node.id === selectedId
        const isDimmed = selectedId != null && !highlightedIds.has(node.id)
        const radius = radii.get(node.id) * (isSelected ? 1.5 : 1)
        return (
          <mesh
            key={node.id}
            position={[node.x, node.y, node.z]}
            scale={radius}
            onClick={(event) => {
              if (event.delta > 4) return // drag, not click
              event.stopPropagation()
              onNodeClick(node.id)
            }}
            onPointerOver={(event) => {
              event.stopPropagation()
              setHoveredId(node.id)
              document.body.style.cursor = 'pointer'
            }}
            onPointerOut={() => {
              setHoveredId((current) => (current === node.id ? null : current))
              document.body.style.cursor = ''
            }}
          >
            <sphereGeometry args={[1, 20, 14]} />
            <meshStandardMaterial
              key={isDimmed ? 'dimmed' : 'solid'} // rebuild the material when transparency changes
              color={networkColors[node.network]}
              emissive={isSelected ? '#ffffff' : '#000000'}
              emissiveIntensity={isSelected ? 0.35 : 0}
              roughness={0.45}
              transparent={isDimmed}
              opacity={isDimmed ? 0.25 : 1}
            />
          </mesh>
        )
      })}

      {hoveredNode && (
        <Html position={[hoveredNode.x, hoveredNode.y, hoveredNode.z]} center style={{ pointerEvents: 'none' }}>
          <div className="hover-label">
            {hoveredNode.hemisphere} · {hoveredNode.name}
          </div>
        </Html>
      )}
    </group>
  )
}
