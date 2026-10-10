import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { hexToRgb, mixRgb } from '../utils/regions.js'

const SURFACE_GRAY = hexToRgb('#b4b1a9')
const MEDIAL_WALL_GRAY = hexToRgb('#6b6964')

// Build a three.js geometry from the exported mesh arrays.
// Input: mesh { points, triangles }. Output: BufferGeometry with normals and a color slot.
function buildGeometry(mesh) {
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(mesh.points, 3))
  geometry.setIndex(new THREE.BufferAttribute(mesh.triangles, 1))
  geometry.computeVertexNormals()
  geometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(mesh.points.length), 3))
  return geometry
}

// One hemisphere's cortical surface.
// Inputs: mesh arrays, nodesById (region id -> node), colorMode ("plain" | "network"),
//         networkColors, hiddenNetworks, selectedId, opacity,
//         onRegionClick(regionId) - called with 0 for the medial wall.
// Output: a three.js mesh element.
export default function BrainSurface({
  mesh, nodesById, colorMode, networkColors, hiddenNetworks, selectedId, opacity, onRegionClick,
}) {
  const geometry = useMemo(() => buildGeometry(mesh), [mesh])
  useEffect(() => () => geometry.dispose(), [geometry])

  // Recolor vertices whenever the color mode, selection, or visible networks change
  useEffect(() => {
    const colors = geometry.getAttribute('color')
    const networkRgb = Object.fromEntries(
      Object.entries(networkColors).map(([network, hex]) => [network, hexToRgb(hex)]),
    )
    for (let vertex = 0; vertex < mesh.regions.length; vertex += 1) {
      const regionId = mesh.regions[vertex]
      let rgb = MEDIAL_WALL_GRAY
      if (regionId > 0) {
        const network = nodesById.get(regionId).network
        rgb = SURFACE_GRAY
        if (colorMode === 'network' && !hiddenNetworks.has(network)) {
          rgb = mixRgb(SURFACE_GRAY, networkRgb[network], 0.75)
        }
        if (regionId === selectedId) {
          rgb = mixRgb(networkRgb[network], [1, 1, 1], 0.15)
        } else if (selectedId != null) {
          rgb = mixRgb(rgb, MEDIAL_WALL_GRAY, 0.35) // dim everything else a little
        }
      }
      colors.setXYZ(vertex, rgb[0], rgb[1], rgb[2])
    }
    colors.needsUpdate = true
  }, [geometry, mesh, nodesById, colorMode, networkColors, hiddenNetworks, selectedId])

  // Clicking the surface: find the clicked triangle's closest corner vertex and look up its region
  function handleClick(event) {
    if (event.delta > 4) return // that was a drag to rotate, not a click
    event.stopPropagation()
    const { a, b, c } = event.face
    const position = geometry.getAttribute('position')
    const corner = new THREE.Vector3()
    let closestVertex = a
    let closestDistance = Infinity
    for (const vertex of [a, b, c]) {
      corner.fromBufferAttribute(position, vertex)
      const distance = corner.distanceTo(event.point)
      if (distance < closestDistance) {
        closestDistance = distance
        closestVertex = vertex
      }
    }
    onRegionClick(mesh.regions[closestVertex])
  }

  const isSeeThrough = opacity < 1
  return (
    <mesh geometry={geometry} onClick={handleClick} renderOrder={isSeeThrough ? 2 : 0}>
      <meshStandardMaterial
        key={isSeeThrough ? 'see-through' : 'solid'} // rebuild the material when switching modes
        vertexColors
        roughness={0.75}
        metalness={0}
        transparent={isSeeThrough}
        opacity={opacity}
        depthWrite={!isSeeThrough}
      />
    </mesh>
  )
}
