import { useMemo } from 'react'
import { Canvas } from '@react-three/fiber'
import { Bvh, OrbitControls } from '@react-three/drei'
import BrainSurface from './BrainSurface.jsx'
import CameraRig, { viewPosition } from './CameraRig.jsx'
import NetworkLayer from './NetworkLayer.jsx'

const BASE_CAMERA_DISTANCE = 340 // mm from the brain's center; fits the whole brain on a wide screen

// The 3D view: both hemispheres, the network layer, lights, and orbit controls.
// Coordinates stay in MNI millimetres (x = left->right, y = back->front, z = down->up),
// so the camera's "up" is +z.
// Inputs: data from loadSubject, view settings, selection state and handlers,
//         viewRequest (preset view to move to), autoRotate, onUserInteract.
// Output: a <Canvas> element filling its container.
export default function BrainScene({
  data, nodesById, networkColors, networkNames, settings, hiddenNetworks, visibleNodes, visibleEdges,
  selectedId, highlightedIds, onSelect, onSurfaceClick, viewRequest, autoRotate, onUserInteract,
}) {
  // Kept stable between renders so panning isn't reset when something else changes
  const { center, distance, startPosition } = useMemo(() => {
    const { min, max } = data.subject.bounding_box_mm
    const middle = min.map((low, axis) => (low + max[axis]) / 2)
    // On tall, narrow screens (phones) start farther back so the whole brain fits across
    const aspect = window.innerWidth / window.innerHeight
    const cameraDistance = BASE_CAMERA_DISTANCE * (aspect < 1 ? 1.1 / aspect : 1)
    return {
      center: middle,
      distance: cameraDistance,
      startPosition: viewPosition('Left', middle, cameraDistance).toArray(), // left lateral view
    }
  }, [data])

  return (
    <Canvas
      camera={{ position: startPosition, up: [0, 0, 1], fov: 35, near: 1, far: 3000 }}
      onPointerMissed={() => onSelect(null)}
      dpr={[1, 2]}
    >
      <color attach="background" args={['#121315']} />
      <hemisphereLight args={['#ffffff', '#3a3a40', 1.0]} position={[0, 0, 1]} />
      <CameraRig viewRequest={viewRequest} center={center} distance={distance} />

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
            networkNames={networkNames}
            selectedId={selectedId}
            highlightedIds={highlightedIds}
            sizeBy={settings.nodeSizeBy}
            center={center}
            onNodeClick={onSelect}
          />
        )}
      </Bvh>

      <OrbitControls
        makeDefault
        target={center}
        enableDamping
        dampingFactor={0.12}
        minDistance={60}
        maxDistance={1200}
        autoRotate={autoRotate}
        autoRotateSpeed={0.6} // about one full turn every 100 seconds
        onStart={onUserInteract}
      />
    </Canvas>
  )
}
