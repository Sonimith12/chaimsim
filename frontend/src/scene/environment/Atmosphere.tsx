import { Environment, Lightformer } from '@react-three/drei'
import { Suspense } from 'react'
import { ErrorBoundary } from '../ErrorBoundary'

// Subtle: the scene stays dark; this only gives surfaces something to reflect.
const INTENSITY = 0.3

/** Offline-safe stand-in used if the "city" preset can't be fetched. */
function LocalEnvironment() {
  return (
    <Environment resolution={256} environmentIntensity={INTENSITY}>
      <Lightformer form="rect" intensity={2} position={[0, 6, -8]} scale={[16, 4, 1]} />
      <Lightformer form="rect" intensity={1} position={[-8, 3, 4]} rotation-y={Math.PI / 2} scale={[8, 3, 1]} />
      <Lightformer form="ring" intensity={1.5} position={[6, 7, 6]} scale={4} color="#8fb4ff" />
    </Environment>
  )
}

/** Environment-map reflections (drei "city" preset), degrading to local lights if it can't load. */
export function Atmosphere() {
  return (
    <ErrorBoundary fallback={<LocalEnvironment />}>
      <Suspense fallback={null}>
        <Environment preset="city" environmentIntensity={INTENSITY} />
      </Suspense>
    </ErrorBoundary>
  )
}
