import { useGLTF } from '@react-three/drei'
import { create } from 'zustand'
import type { NodeType } from '../../types/sim'

export type ModelKey = 'supplier' | 'distribution_center' | 'retailer' | 'truck' | 'crate'

/** Where each model is served from (see public/models/README.md). */
export const MODEL_PATHS: Record<ModelKey, string> = {
  supplier: '/models/factory.glb',
  distribution_center: '/models/warehouse.glb',
  retailer: '/models/store.glb',
  truck: '/models/truck.glb',
  crate: '/models/crate.glb',
}

/**
 * Target size, in world units, of each model's longest horizontal dimension.
 * Models are auto-scaled to this, so any downloaded asset lands at the right size.
 */
export const MODEL_FIT: Record<ModelKey, number> = {
  supplier: 2.9, // factory: the biggest building
  distribution_center: 2.5, // warehouse: slightly smaller
  retailer: 2.0, // store: smallest
  truck: 1.05,
  crate: 0.34,
}

/** Extra yaw (radians) for a truck model whose "front" isn't +Z. */
export const TRUCK_HEADING_OFFSET = 0

export const NODE_MODEL_KEY: Record<NodeType, ModelKey> = {
  Supplier: 'supplier',
  Manufacturer: 'supplier',
  DistributionCenter: 'distribution_center',
  Retailer: 'retailer',
}

export type ModelStatus = 'pending' | 'ready' | 'missing'

interface ModelStore {
  status: Record<ModelKey, ModelStatus>
}

export const useModelStore = create<ModelStore>(() => ({
  status: {
    supplier: 'pending',
    distribution_center: 'pending',
    retailer: 'pending',
    truck: 'pending',
    crate: 'pending',
  },
}))

/** Hook: has this model's file been confirmed present? Placeholders render until then. */
export function useModelReady(key: ModelKey): boolean {
  return useModelStore((s) => s.status[key] === 'ready')
}

/**
 * True only for a real binary glTF. A plain existence check isn't enough: the
 * Vite dev server answers unknown paths with index.html and a 200.
 */
async function isGlb(path: string): Promise<boolean> {
  try {
    const res = await fetch(path)
    if (!res.ok || !res.body) return false
    const reader = res.body.getReader()
    const { value } = await reader.read()
    void reader.cancel()
    if (!value || value.length < 4) return false
    return String.fromCharCode(value[0], value[1], value[2], value[3]) === 'glTF'
  } catch {
    return false
  }
}

/** Check which model files exist and preload the ones that do. Safe to call with none present. */
export async function probeModels(): Promise<void> {
  const keys = Object.keys(MODEL_PATHS) as ModelKey[]
  await Promise.all(
    keys.map(async (key) => {
      const ok = await isGlb(MODEL_PATHS[key])
      if (ok) useGLTF.preload(MODEL_PATHS[key])
      useModelStore.setState((s) => ({
        status: { ...s.status, [key]: ok ? 'ready' : 'missing' },
      }))
    }),
  )
}
