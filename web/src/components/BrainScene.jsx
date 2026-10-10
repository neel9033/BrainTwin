import { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Bvh, OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import BrainSurface from './BrainSurface.jsx'
import CameraRig, { viewPosition } from './CameraRig.jsx'
import NetworkLayer from './NetworkLayer.jsx'

const BASE_CAMERA_DISTANCE = 340 // mm from the brain's center; fits the whole brain on a wide screen
export const SCENE_BACKGROUND = '#0e131a' // very dark blue-grey (matches --background in styles.css)

// A light shining from above-front-left that casts soft shadows, so nodes look
// like they sit on the cortex. It points at the brain's center.
// Input: center [x,y,z]. Output: a directional light plus its aiming target.
function KeyLight({ center }) {
  const target = useMemo(() => new THREE.Object3D(), [])
  return (
    <>
      <primitive object={target} position={center} />
      <directionalLight
        target={target}
        // above, in front and to the left, at a moderate angle so each node's shadow
        // falls beside it on the cortex instead of hiding directly underneath
        position={[center[0] - 200, center[1] + 130, center[2] + 170]}
        intensity={1.5}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-radius={5} // blurs the shadow edge so it reads as soft
        shadow-bias={-0.0004}
        shadow-normalBias={0.6}
        shadow-camera-left={-130}
        shadow-camera-right={130}
        shadow-camera-top={130}
        shadow-camera-bottom={-130}
        shadow-camera-near={10}
        shadow-camera-far={700}
      />
    </>
  )
}

// Calls onFirstFrame once, after the scene has actually been drawn.
// Input: onFirstFrame(). Output: nothing visible.
function FirstFrameSignal({ onFirstFrame }) {
  const reported = useRef(false)
  useFrame(() => {
    if (!reported.current) {
      reported.current = true
      // wait one more frame so the picture is on screen before the loader fades
      requestAnimationFrame(() => onFirstFrame?.())
    }
  })
  return null
}

// The 3D view: both hemispheres, the network layer, lights, fog and orbit controls.
// Coordinates stay in MNI millimetres (x = left->right, y = back->front, z = down->up),
// so the camera's "up" is +z.
// Inputs: data from loadSubject, view settings, selection state and handlers,
//         viewRequest (preset view to move to), autoRotate, onUserInteract, onFirstFrame.
// Output: a <Canvas> element filling its container.
export default function BrainScene({
  data, nodesById, networkColors, networkNames, settings, hiddenNetworks, visibleNodes, visibleEdges,
  selectedId, highlightedIds, onSelect, onSurfaceClick, viewRequest, autoRotate, onUserInteract, onFirstFrame,
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
      shadows="percentage" // PCF shadows; softened with shadow-radius on the key light
    >
      <color attach="background" args={[SCENE_BACKGROUND]} />
      {/* Depth fog: CameraRig keeps its start/end just around the brain as you zoom */}
      <fog attach="fog" args={[SCENE_BACKGROUND, 300, 520]} />
      <hemisphereLight args={['#dfe8ff', '#1c2230', 0.6]} position={[0, 0, 1]} />
      <KeyLight center={center} />
      <CameraRig viewRequest={viewRequest} center={center} distance={distance} />
      <FirstFrameSignal onFirstFrame={onFirstFrame} />

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
