import { useEffect, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'

// Preset views. Each is the direction from the brain's center to the camera,
// in MNI axes (x = left->right, y = back->front, z = down->up).
// "Top" is nudged slightly toward the back so "up" on screen is the front of the brain.
export const VIEW_DIRECTIONS = {
  Left: [-1, 0, 0],
  Right: [1, 0, 0],
  Top: [0, -0.001, 1],
  Front: [0, 1, 0],
  Back: [0, -1, 0],
}
const MOVE_SECONDS = 0.7

// Where the camera should sit for a preset view.
// Inputs: view name, brain center [x,y,z], distance in mm. Output: THREE.Vector3.
export function viewPosition(viewName, center, distance) {
  const direction = new THREE.Vector3(...VIEW_DIRECTIONS[viewName]).normalize()
  return new THREE.Vector3(...center).addScaledVector(direction, distance)
}

// Moves the camera smoothly to a preset view whenever viewRequest changes,
// and keeps a light shining from the camera so every side of the brain is lit.
// Inputs: viewRequest { name, id } (id changes on every button press so the same
//         view can be requested twice), center [x,y,z], distance (mm).
// Output: a light; the camera movement happens in useFrame.
export default function CameraRig({ viewRequest, center, distance }) {
  const { camera, controls } = useThree()
  const lightRef = useRef()
  const move = useRef(null) // { from, to, elapsed } while a move is running

  // Start a move when a new view is requested. The camera swings around the brain
  // (rotating its direction from the center) instead of cutting straight through it.
  useEffect(() => {
    if (!viewRequest) return
    const centerVector = new THREE.Vector3(...center)
    const fromOffset = camera.position.clone().sub(centerVector)
    const toOffset = viewPosition(viewRequest.name, center, distance).sub(centerVector)
    move.current = {
      fromDirection: fromOffset.clone().normalize(),
      fromDistance: fromOffset.length(),
      fullTurn: new THREE.Quaternion().setFromUnitVectors(
        fromOffset.clone().normalize(), toOffset.clone().normalize()),
      toDistance: toOffset.length(),
      elapsed: 0,
    }
  }, [viewRequest, camera, center, distance])

  // If the user grabs the controls mid-move, let them take over
  useEffect(() => {
    if (!controls) return undefined
    const cancelMove = () => {
      move.current = null
    }
    controls.addEventListener('start', cancelMove)
    return () => controls.removeEventListener('start', cancelMove)
  }, [controls])

  useFrame((_state, delta) => {
    if (move.current && controls) {
      const current = move.current
      current.elapsed += delta
      const progress = Math.min(1, current.elapsed / MOVE_SECONDS)
      const eased = 1 - Math.pow(1 - progress, 3) // fast start, gentle stop
      const partTurn = new THREE.Quaternion().slerp(current.fullTurn, eased)
      const direction = current.fromDirection.clone().applyQuaternion(partTurn)
      const cameraDistance = THREE.MathUtils.lerp(current.fromDistance, current.toDistance, eased)
      camera.position.set(...center).addScaledVector(direction, cameraDistance)
      controls.target.set(...center)
      controls.update()
      if (progress === 1) move.current = null
    }
    if (lightRef.current) lightRef.current.position.copy(camera.position)
  })

  return <directionalLight ref={lightRef} intensity={1.2} />
}
