import { Color } from 'three'
import type { ThreeElements } from '@react-three/fiber'

/**
 * What the node wants its body to look like this frame. The node component
 * updates it every frame; whichever body is showing (placeholder box or a
 * real model) reads it, so highlights work identically for both.
 */
export interface Appearance {
  /** Base colour for the placeholder box (tinted orange on backlog, dark red offline). */
  tint: Color
  /** Hover / selection / stockout glow for the placeholder box. */
  glow: Color
  glowIntensity: number
  /** Same, for model materials (their own colours are left alone). */
  modelGlow: Color
  modelGlowIntensity: number
}

export function createAppearance(color: string): Appearance {
  return {
    tint: new Color(color),
    glow: new Color(color),
    glowIntensity: 0,
    modelGlow: new Color('#000000'),
    modelGlowIntensity: 0,
  }
}

export type NodeHandlers = Pick<
  ThreeElements['group'],
  'onClick' | 'onDoubleClick' | 'onPointerOver' | 'onPointerOut' | 'onPointerDown' | 'onContextMenu'
>

export type Size3 = [number, number, number]

/** Footprint of the placeholder box; also the default before a model is measured. */
export const PLACEHOLDER_SIZE: Size3 = [2.2, 1.4, 2.2]
