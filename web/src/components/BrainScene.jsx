import { useMemo } from 'react'
import { Canvas } from '@react-three/fiber'
import { Bvh, OrbitControls } from '@react-three/drei'
import BrainSurface from './BrainSurface.jsx'
import NetworkLayer from './NetworkLayer.jsx'

// The 3D view: both hemispheres, the network layer, lights, and orbit controls.
// Coordinates stay in MNI millimetres (x = left->right, y = back->front, z = down->up),
// so the camera's "up" is +z.
// Inputs: data from loadSubject, view settings, and selection handlers (see App.jsx).
// Output: a <Canvas> element filling its container.
export default function BrainScene({
  data, nodesById, networkColors, settings, hiddenNetworks, visibleNodes, visibleEdges,
  selectedId, highlightedIds, onSelect, onSurfaceClick,
}) {
  // Kept stable between renders so panning isn't reset when something else changes
  const { center, cameraPosition } = useMemo(() => {
    const { min, max } = data.subject.bounding_box_mm
    const middle = min.map((low, axis) => (low + max[axis]) / 2)
    // Start looking at the left hemisphere from slightly in front and above.
    // On tall, narrow screens (phones) start farther back so the whole brain fits across.
    const aspect = window.innerWidth / window.innerHeight
    const zoomOut = aspect < 1 ? 1.1 / aspect : 1
    const offset = [-300, 110, 120].map((value) => value * zoomOut)
    return { center: middle, cameraPosition: middle.map((value, axis) => value + offset[axis]) }
  }, [data])

  return (
    <Canvas
      camera={{ position: cameraPosition, up: [0, 0, 1], fov: 35, near: 1, far: 3000 }}
      onPointerMissed={() => onSelect(null)}
      dpr={[1, 2]}
    >
      <color attach="background" args={['#121315']} />
      <hemisphereLight args={['#ffffff', '#3a3a40', 0.9]} position={[0, 0, 1]} />
      <directionalLight position={[-250, 200, 300]} intensity={1.4} />
      <directionalLight position={[250, -150, 100]} intensity={0.7} />

      <Bvh firstHitOnly>
        {settings.showSurface &&
          ['L', 'R'].map((hemisphere) => (
            <BrainSurface
              key={hemisphere}
              mesh={data.meshes[hemisphere]}
              nodesById={nodesById}
              colorMode={settings.surfaceColorMode}
              networkColors={networkColors}
              hiddenNetworks={hiddenNetworks}
              selectedId={selectedId}
              opacity={settings.surfaceOpacity}
              onRegionClick={onSurfaceClick}
            />
          ))}
        {settings.showNetwork && (
          <NetworkLayer
            visibleNodes={visibleNodes}
            visibleEdges={visibleEdges}
            nodesById={nodesById}
            networkColors={networkColors}
            selectedId={selectedId}
            highlightedIds={highlightedIds}
            sizeBy={settings.nodeSizeBy}
            onNodeClick={onSelect}
          />
        )}
      </Bvh>

      <OrbitControls makeDefault target={center} enableDamping dampingFactor={0.12} minDistance={60} maxDistance={900} />
    </Canvas>
  )
}
