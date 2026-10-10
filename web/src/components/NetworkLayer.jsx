import { useMemo, useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { Html, Line } from '@react-three/drei'
import * as THREE from 'three'
import { hemisphereName, hexToRgb, mixRgb, regionTitle } from '../utils/regions.js'

// Edges are drawn in strength bands: stronger connections are thicker and more opaque.
// (WebGL can't vary line width per line, so each band is drawn as one batch.)
const EDGE_BANDS = [
  { minWeight: -1, width: 0.6, opacity: 0.18 },
  { minWeight: 0.4, width: 1.1, opacity: 0.3 },
  { minWeight: 0.55, width: 1.8, opacity: 0.5 },
  { minWeight: 0.7, width: 2.8, opacity: 0.8 },
]
// Unrelated edges while a region is selected: one thin, almost invisible batch
const FADED_BAND = { minWeight: -1, width: 0.5, opacity: 0.03 }
const FADED_NODE_OPACITY = 0.06

const BASE_NODE_RADIUS = 2.2 // mm
const ARC_SEGMENTS = 10 // straight pieces per curved edge
const ARC_BULGE = 0.22 // how far an arc bows out, as a fraction of its length
const HOVER_GROWTH = 1.35
const SELECTED_GROWTH = 1.5

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

// Points along a curved arc between two nodes. The arc bows away from the brain's
// center (a quadratic curve), so overlapping connections separate into distinct paths.
// Inputs: start and end [x,y,z], center [x,y,z]. Output: array of ARC_SEGMENTS + 1 [x,y,z] points.
function arcPoints(start, end, center) {
  const startVector = new THREE.Vector3(...start)
  const endVector = new THREE.Vector3(...end)
  const middle = startVector.clone().add(endVector).multiplyScalar(0.5)
  const outward = middle.clone().sub(new THREE.Vector3(...center))
  if (outward.lengthSq() < 1) outward.set(0, 0, 1) // midpoint at the center: bow upward
  outward.normalize()
  const control = middle.addScaledVector(outward, ARC_BULGE * startVector.distanceTo(endVector))
  const curve = new THREE.QuadraticBezierCurve3(startVector, control, endVector)
  return curve.getPoints(ARC_SEGMENTS).map((point) => [point.x, point.y, point.z])
}

// Turn edges into curved line segments, grouped into strength bands.
// Inputs: edges, nodesById, networkRgb (network -> [r,g,b]), center,
//         bands (list of bands; edges go into the strongest band they reach).
// Output: array of { band, points, colors } for non-empty bands. Colors fade from the
//         source region's network color to the target's along each arc.
function arcBatches(edges, nodesById, networkRgb, center, bands) {
  const batches = bands.map((band) => ({ band, points: [], colors: [] }))
  for (const edge of edges) {
    let bandIndex = 0
    bands.forEach((band, index) => {
      if (edge.weight >= band.minWeight) bandIndex = index
    })
    const source = nodesById.get(edge.source)
    const target = nodesById.get(edge.target)
    const sourceColor = networkRgb[source.network]
    const targetColor = networkRgb[target.network]
    const points = arcPoints([source.x, source.y, source.z], [target.x, target.y, target.z], center)
    const batch = batches[bandIndex]
    for (let piece = 0; piece < ARC_SEGMENTS; piece += 1) {
      // each straight piece is one line segment: (point i, point i+1)
      batch.points.push(points[piece], points[piece + 1])
      batch.colors.push(
        mixRgb(sourceColor, targetColor, piece / ARC_SEGMENTS),
        mixRgb(sourceColor, targetColor, (piece + 1) / ARC_SEGMENTS),
      )
    }
  }
  return batches.filter((batch) => batch.points.length > 0)
}

// Draw one batch of arcs.
// Inputs: batch { band, points, colors }, opacity. Output: a drei <Line>.
function ArcBatch({ batch, opacity }) {
  return (
    <Line
      points={batch.points}
      vertexColors={batch.colors}
      segments
      lineWidth={batch.band.width}
      transparent
      opacity={opacity}
      depthWrite={false}
      renderOrder={1}
    />
  )
}

// One node sphere. Its size eases toward the target size, so hovering or selecting
// makes it grow smoothly instead of jumping.
// Inputs: node, geometry (shared sphere), color, radius, isSelected, isHovered, isFaded,
//         and pointer handlers. Output: a three.js mesh.
function NodeSphere({ node, geometry, color, radius, isSelected, isHovered, isFaded, onClick, onHover, onUnhover }) {
  const meshRef = useRef()
  const targetRadius = radius * (isSelected ? SELECTED_GROWTH : isHovered ? HOVER_GROWTH : 1)

  useFrame((_state, delta) => {
    const mesh = meshRef.current
    if (!mesh) return
    mesh.scale.setScalar(THREE.MathUtils.damp(mesh.scale.x, targetRadius, 14, delta))
  })

  return (
    <mesh
      ref={meshRef}
      geometry={geometry}
      position={[node.x, node.y, node.z]}
      scale={0.001} // starts tiny and grows in on load
      onClick={(event) => {
        if (event.delta > 4) return // drag, not click
        event.stopPropagation()
        onClick(node.id)
      }}
      onPointerOver={(event) => {
        event.stopPropagation()
        onHover(node.id)
      }}
      onPointerOut={() => onUnhover(node.id)}
    >
      <meshStandardMaterial
        key={isFaded ? 'faded' : 'solid'} // rebuild the material when transparency changes
        color={color}
        emissive={isSelected || isHovered ? '#ffffff' : '#000000'}
        emissiveIntensity={isSelected ? 0.35 : isHovered ? 0.2 : 0}
        roughness={0.45}
        transparent={isFaded}
        opacity={isFaded ? FADED_NODE_OPACITY : 1}
        depthWrite={!isFaded}
      />
    </mesh>
  )
}

// Nodes (spheres colored by network) and edges (curved arcs weighted by strength).
// When a region is selected, only its connections are drawn clearly; everything
// unrelated fades to almost invisible.
// Inputs: visibleNodes, visibleEdges (already filtered by threshold and networks),
//         nodesById, networkColors, networkNames, selectedId,
//         highlightedIds (selected region + its partners), sizeBy, center, onNodeClick(id).
// Output: a group of three.js objects.
export default function NetworkLayer({
  visibleNodes, visibleEdges, nodesById, networkColors, networkNames, selectedId, highlightedIds,
  sizeBy, center, onNodeClick,
}) {
  const [hoveredId, setHoveredId] = useState(null)
  const sphere = useMemo(() => new THREE.SphereGeometry(1, 24, 16), [])
  const networkRgb = useMemo(
    () => Object.fromEntries(Object.entries(networkColors).map(([network, hex]) => [network, hexToRgb(hex)])),
    [networkColors],
  )
  const radii = useMemo(() => nodeRadii(visibleNodes, sizeBy), [visibleNodes, sizeBy])

  // Split edges into the selected region's connections and everything else
  const { mainBatches, fadedBatches } = useMemo(() => {
    const touchesSelected = (edge) => edge.source === selectedId || edge.target === selectedId
    const mainEdges = selectedId == null ? visibleEdges : visibleEdges.filter(touchesSelected)
    const otherEdges = selectedId == null ? [] : visibleEdges.filter((edge) => !touchesSelected(edge))
    return {
      mainBatches: arcBatches(mainEdges, nodesById, networkRgb, center, EDGE_BANDS),
      fadedBatches: arcBatches(otherEdges, nodesById, networkRgb, center, [FADED_BAND]),
    }
  }, [visibleEdges, selectedId, nodesById, networkRgb, center])

  // Show the hover tooltip and pointer cursor
  function handleHover(nodeId) {
    setHoveredId(nodeId)
    document.body.style.cursor = 'pointer'
  }
  // Hide them again (only if this node is still the hovered one)
  function handleUnhover(nodeId) {
    setHoveredId((current) => (current === nodeId ? null : current))
    document.body.style.cursor = ''
  }

  const hoveredNode = hoveredId != null ? nodesById.get(hoveredId) : null
  const hoveredRadius = hoveredNode ? (radii.get(hoveredNode.id) || BASE_NODE_RADIUS) * HOVER_GROWTH : 0

  return (
    <group>
      {fadedBatches.map((batch) => (
        <ArcBatch key={`faded-${batch.points.length}`} batch={batch} opacity={batch.band.opacity} />
      ))}
      {mainBatches.map((batch) => (
        <ArcBatch
          key={`${batch.band.minWeight}-${batch.points.length}`}
          batch={batch}
          opacity={selectedId != null ? Math.min(1, batch.band.opacity + 0.3) : batch.band.opacity}
        />
      ))}

      {visibleNodes.map((node) => (
        <NodeSphere
          key={node.id}
          node={node}
          geometry={sphere}
          color={networkColors[node.network]}
          radius={radii.get(node.id)}
          isSelected={node.id === selectedId}
          isHovered={node.id === hoveredId}
          isFaded={selectedId != null && !highlightedIds.has(node.id)}
          onClick={onNodeClick}
          onHover={handleHover}
          onUnhover={handleUnhover}
        />
      ))}

      {hoveredNode && (
        <Html
          position={[hoveredNode.x, hoveredNode.y, hoveredNode.z + hoveredRadius]}
          center
          zIndexRange={[20, 0]}
          style={{ pointerEvents: 'none' }}
        >
          <div className="hover-label">
            <span className="hover-title">
              <span className="swatch" style={{ background: networkColors[hoveredNode.network] }} />
              {regionTitle(hoveredNode, networkNames)}
            </span>
            <span className="hover-detail">
              {networkNames[hoveredNode.network]} · {hemisphereName(hoveredNode.hemisphere)}
            </span>
          </div>
        </Html>
      )}
    </group>
  )
}
