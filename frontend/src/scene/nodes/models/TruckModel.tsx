import { MODEL_FIT, MODEL_PATHS, TRUCK_HEADING_OFFSET } from '../../models/ModelRegistry'
import { useFittedModel } from '../../models/useFittedModel'

/**
 * A truck model facing +Z at heading 0 (adjust TRUCK_HEADING_OFFSET for assets
 * that face another way). The parent rotates it to the direction of travel.
 */
export function TruckModel() {
  const fitted = useFittedModel(MODEL_PATHS.truck, MODEL_FIT.truck)
  return (
    <group rotation-y={TRUCK_HEADING_OFFSET}>
      <primitive object={fitted.root} scale={fitted.scale} position={fitted.offset} />
    </group>
  )
}
