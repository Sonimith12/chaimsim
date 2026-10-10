import { useGLTF } from '@react-three/drei'
import { useMemo } from 'react'
import { Box3, Material, Mesh, Vector3, type Object3D } from 'three'

export interface FittedModel {
  root: Object3D
  /** Uniform scale that brings the model's longest horizontal side to the target. */
  scale: number
  /** Offset (already in scaled units) that centres it on x/z and sits it on y = 0. */
  offset: [number, number, number]
  /** Scaled bounding size [x, y, z]. */
  size: [number, number, number]
  /** This instance's own materials, safe to mutate per node. */
  materials: Material[]
}

/**
 * Loads a glb and returns a private, auto-fitted clone of it. Private so that
 * per-node emissive highlighting doesn't leak into other instances of the model.
 */
export function useFittedModel(path: string, target: number): FittedModel {
  const gltf = useGLTF(path)
  return useMemo(() => {
    const root = gltf.scene.clone(true)
    const materials: Material[] = []
    root.traverse((obj) => {
      if (!(obj instanceof Mesh)) return
      obj.castShadow = true
      obj.receiveShadow = true
      const cloned = Array.isArray(obj.material)
        ? obj.material.map((m: Material) => m.clone())
        : obj.material.clone()
      obj.material = cloned
      materials.push(...(Array.isArray(cloned) ? cloned : [cloned]))
    })

    const box = new Box3().setFromObject(root)
    const size = box.getSize(new Vector3())
    const center = box.getCenter(new Vector3())
    const longest = Math.max(size.x, size.z, 1e-6)
    const scale = target / longest
    return {
      root,
      scale,
      offset: [-center.x * scale, -box.min.y * scale, -center.z * scale],
      size: [size.x * scale, size.y * scale, size.z * scale],
      materials,
    }
  }, [gltf, target])
}
