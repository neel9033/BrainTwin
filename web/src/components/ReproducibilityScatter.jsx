import { useEffect, useMemo, useRef, useState } from 'react'
import { regionTitle } from '../utils/regions.js'

const AXIS_MIN = -0.8
const AXIS_MAX = 1.0
const PADDING = { left: 30, right: 8, top: 8, bottom: 28 } // room for tick labels, in CSS pixels
const TICKS = [-0.5, 0, 0.5, 1]
const COLORS = {
  sameNetwork: 'rgba(127, 178, 240, 0.42)',
  otherNetwork: 'rgba(150, 165, 190, 0.2)',
  selected: '#f5c26b',
  grid: 'rgba(160, 180, 210, 0.1)',
  diagonal: 'rgba(230, 235, 242, 0.55)',
  label: '#8e9aab',
  ring: '#0e131a',
}
const HOVER_RADIUS = 7 // px: how close the pointer must be to a dot

// Pair every region with every later region, in the same order as comparison_edges.bin
// (upper triangle of the matrix: 1-2, 1-3, ... 199-200).
// Input: number of regions. Output: { first, second } Uint16Arrays of node positions.
function buildPairs(regionCount) {
  const pairCount = (regionCount * (regionCount - 1)) / 2
  const first = new Uint16Array(pairCount)
  const second = new Uint16Array(pairCount)
  let pair = 0
  for (let row = 0; row < regionCount; row += 1) {
    for (let column = row + 1; column < regionCount; column += 1) {
      first[pair] = row
      second[pair] = column
      pair += 1
    }
  }
  return { first, second }
}

// Scatter plot of every connection's strength in scan 1 (across) against scan 2 (up).
// Dots near the diagonal mean the two scans agree.
// Inputs: pairValues (Float32Array: r in scan 1, r in scan 2, for each pair), nodes (in id
//         order), networkNames, runLabels ["REST1", "REST2"], selectedId, size (px).
// Output: a canvas with a hover tooltip and a legend.
export default function ReproducibilityScatter({ pairValues, nodes, networkNames, runLabels, selectedId, size = 244 }) {
  const canvasRef = useRef(null)
  const baseLayerRef = useRef(null) // all 19,900 dots, drawn once
  const [hovered, setHovered] = useState(null) // { pair, x, y }
  const pairs = useMemo(() => buildPairs(nodes.length), [nodes.length])
  const plotSize = size - PADDING.left - PADDING.right

  // Data value -> pixel position inside the canvas
  const toX = (value) => PADDING.left + ((value - AXIS_MIN) / (AXIS_MAX - AXIS_MIN)) * plotSize
  const toY = (value) => PADDING.top + (1 - (value - AXIS_MIN) / (AXIS_MAX - AXIS_MIN)) * plotSize

  // Draw grid, diagonal and every dot once into an offscreen canvas
  useEffect(() => {
    const scale = window.devicePixelRatio || 1
    const layer = document.createElement('canvas')
    layer.width = size * scale
    layer.height = size * scale
    const context = layer.getContext('2d')
    context.scale(scale, scale)

    context.strokeStyle = COLORS.grid
    context.lineWidth = 1
    context.fillStyle = COLORS.label
    context.font = '10px ui-monospace, SF Mono, Menlo, monospace'
    for (const tick of TICKS) {
      context.beginPath()
      context.moveTo(toX(tick), PADDING.top)
      context.lineTo(toX(tick), PADDING.top + plotSize)
      context.moveTo(PADDING.left, toY(tick))
      context.lineTo(PADDING.left + plotSize, toY(tick))
      context.stroke()
      context.textAlign = 'center'
      context.fillText(String(tick), toX(tick), PADDING.top + plotSize + 12)
      context.textAlign = 'right'
      context.fillText(String(tick), PADDING.left - 4, toY(tick) + 3)
    }
    context.font = '11px system-ui, sans-serif'
    context.textAlign = 'center'
    context.fillText(`${runLabels[0]}  →`, PADDING.left + plotSize / 2, size - 3)
    context.save()
    context.translate(10, PADDING.top + plotSize / 2)
    context.rotate(-Math.PI / 2)
    context.fillText(`${runLabels[1]}  →`, 0, 0)
    context.restore()

    // Different-network pairs first, then same-network pairs on top
    for (const drawSameNetwork of [false, true]) {
      context.fillStyle = drawSameNetwork ? COLORS.sameNetwork : COLORS.otherNetwork
      for (let pair = 0; pair < pairs.first.length; pair += 1) {
        const sameNetwork = nodes[pairs.first[pair]].network === nodes[pairs.second[pair]].network
        if (sameNetwork !== drawSameNetwork) continue
        context.fillRect(toX(pairValues[2 * pair]) - 0.9, toY(pairValues[2 * pair + 1]) - 0.9, 1.8, 1.8)
      }
    }

    context.setLineDash([4, 3])
    context.strokeStyle = COLORS.diagonal
    context.beginPath()
    context.moveTo(toX(AXIS_MIN), toY(AXIS_MIN))
    context.lineTo(toX(AXIS_MAX), toY(AXIS_MAX))
    context.stroke()
    baseLayerRef.current = layer
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pairValues, nodes, pairs, size, runLabels])

  // Copy the base layer, then draw the selected region's connections and the hovered dot
  useEffect(() => {
    const canvas = canvasRef.current
    const layer = baseLayerRef.current
    if (!canvas || !layer) return
    const scale = window.devicePixelRatio || 1
    canvas.width = size * scale
    canvas.height = size * scale
    const context = canvas.getContext('2d')
    context.drawImage(layer, 0, 0)
    context.scale(scale, scale)

    function drawDot(pair, radius, color) {
      context.beginPath()
      context.arc(toX(pairValues[2 * pair]), toY(pairValues[2 * pair + 1]), radius, 0, Math.PI * 2)
      context.fillStyle = color
      context.fill()
      context.lineWidth = 1
      context.strokeStyle = COLORS.ring
      context.stroke()
    }
    if (selectedId != null) {
      const selectedIndex = nodes.findIndex((node) => node.id === selectedId)
      for (let pair = 0; pair < pairs.first.length; pair += 1) {
        if (pairs.first[pair] === selectedIndex || pairs.second[pair] === selectedIndex) {
          drawDot(pair, 2.6, COLORS.selected)
        }
      }
    }
    if (hovered) drawDot(hovered.pair, 4, '#ffffff')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, hovered, pairValues, nodes, pairs, size, runLabels])

  // Find the dot nearest the pointer (only checks dots in the pointer's neighbourhood)
  function handlePointerMove(event) {
    const box = canvasRef.current.getBoundingClientRect()
    const x = event.clientX - box.left
    const y = event.clientY - box.top
    let nearest = null
    let nearestDistance = HOVER_RADIUS
    for (let pair = 0; pair < pairs.first.length; pair += 1) {
      const dx = toX(pairValues[2 * pair]) - x
      if (dx > HOVER_RADIUS || dx < -HOVER_RADIUS) continue
      const dy = toY(pairValues[2 * pair + 1]) - y
      const distance = Math.hypot(dx, dy)
      if (distance < nearestDistance) {
        nearestDistance = distance
        nearest = pair
      }
    }
    setHovered(nearest == null ? null : { pair: nearest, x, y })
  }

  const hoveredInfo = hovered && {
    first: nodes[pairs.first[hovered.pair]],
    second: nodes[pairs.second[hovered.pair]],
    values: [pairValues[2 * hovered.pair], pairValues[2 * hovered.pair + 1]],
  }

  return (
    <div className="scatter">
      <div className="scatter-canvas-wrap" style={{ width: size, height: size }}>
        <canvas
          ref={canvasRef}
          style={{ width: size, height: size }}
          role="img"
          aria-label={`Scatter plot of ${pairs.first.length.toLocaleString()} connections: strength in ${runLabels[0]} across, ${runLabels[1]} up.`}
          onPointerMove={handlePointerMove}
          onPointerLeave={() => setHovered(null)}
        />
        {hoveredInfo && (
          <div
            className="scatter-tooltip"
            style={{ left: Math.min(hovered.x + 10, size - 150), top: Math.max(hovered.y - 58, 0) }}
          >
            <strong>
              {regionTitle(hoveredInfo.first, networkNames)} ({hoveredInfo.first.hemisphere}) ↔{' '}
              {regionTitle(hoveredInfo.second, networkNames)} ({hoveredInfo.second.hemisphere})
            </strong>
            <span>
              {runLabels[0]} <span className="number">{hoveredInfo.values[0].toFixed(2)}</span> · {runLabels[1]}{' '}
              <span className="number">{hoveredInfo.values[1].toFixed(2)}</span>
            </span>
          </div>
        )}
      </div>
      <ul className="scatter-legend">
        <li><span className="legend-dot" style={{ background: 'rgb(127, 178, 240)' }} />Both regions in the same network</li>
        <li><span className="legend-dot" style={{ background: 'rgb(150, 165, 190)' }} />Regions in different networks</li>
        {selectedId != null && (
          <li><span className="legend-dot" style={{ background: COLORS.selected }} />The selected region's connections</li>
        )}
        <li><span className="legend-dash" />Perfect agreement</li>
      </ul>
    </div>
  )
}
