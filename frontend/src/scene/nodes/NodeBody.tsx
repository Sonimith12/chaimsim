import { Suspense, useCallback, type ComponentType } from 'react'
import { ErrorBoundary } from '../ErrorBoundary'
import { NODE_MODEL_KEY, useModelReady, type ModelKey } from '../models/ModelRegistry'
import type { NodeType } from '../../types/sim'
import type { BuildingProps } from './models/BuildingModel'
import { FactoryModel } from './models/FactoryModel'
import { StoreModel } from './models/StoreModel'
import { WarehouseModel } from './models/WarehouseModel'
import { PlaceholderBody } from './PlaceholderBody'
import type { Appearance, NodeHandlers, Size3 } from './appearance'

const MODEL_COMPONENTS: Partial<Record<ModelKey, ComponentType<BuildingProps>>> = {
  supplier: FactoryModel,
  distribution_center: WarehouseModel,
  retailer: StoreModel,
}

interface Props {
  type: NodeType
  baseColor: string
  appearance: React.RefObject<Appearance>
  handlers: NodeHandlers
  phase: number
  onMeasured: (size: Size3) => void
}

/** The node's visible body: its real model when the .glb is present, else the placeholder box. */
export function NodeBody({ type, baseColor, appearance, handlers, phase, onMeasured }: Props) {
  const key = NODE_MODEL_KEY[type]
  const ready = useModelReady(key)
  const Model = MODEL_COMPONENTS[key]
  const measured = useCallback(onMeasured, [onMeasured])

  const placeholder = (
    <PlaceholderBody
      appearance={appearance}
      handlers={handlers}
      onMeasured={measured}
      baseColor={baseColor}
    />
  )
  if (!ready || !Model) return placeholder

  return (
    <ErrorBoundary fallback={placeholder}>
      <Suspense fallback={placeholder}>
        <Model appearance={appearance} handlers={handlers} phase={phase} onMeasured={measured} />
      </Suspense>
    </ErrorBoundary>
  )
}
