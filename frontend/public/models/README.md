# 3D models

The game runs without any of these files: every model falls back to a coloured
placeholder box. Drop `.glb` files here (names are exact) and reload — they are
detected at startup, preloaded, and swapped in automatically. Nothing needs a
code change, and `.glb` files here are git-ignored.

| File            | Used for                                   | Placeholder if missing |
| --------------- | ------------------------------------------ | ---------------------- |
| `factory.glb`   | Suppliers and manufacturers (largest)      | blue box               |
| `warehouse.glb` | Distribution centres (slightly smaller)    | yellow box             |
| `store.glb`     | Retailers (smallest)                       | green box              |
| `truck.glb`     | Shipments travelling along edges           | small box              |
| `crate.glb`     | One unit of inventory (optional)           | wooden cube            |

## Requirements

- Binary glTF (`.glb`), not `.gltf` + separate files. Files that are not real
  glTF binaries are ignored.
- Any scale or origin: each model is automatically scaled so its longest
  horizontal side matches a target size and is centred on the ground. Target
  sizes live in `MODEL_FIT` in `src/scene/models/ModelRegistry.ts`.
- Y-up, wheels/base at the bottom.
- **Trucks should face +Z.** If your truck drives sideways or backwards, set
  `TRUCK_HEADING_OFFSET` (radians) in `ModelRegistry.ts`, e.g. `Math.PI` or
  `Math.PI / 2`.
- Keep them low-poly (a few thousand triangles each) — several copies of each
  appear on screen. Draco-compressed files are supported.

## Where to get them (all free)

- **Kenney** — https://kenney.nl/assets (CC0). Good packs: *City Kit
  (Industrial)*, *City Kit (Commercial)*, *Car Kit* (a truck), *Conveyor Kit*,
  *Retro Medieval Kit*'s crates, or *Furniture Kit* for boxes. Kenney ships
  `.glb` in the download.
- **Quaternius** — https://quaternius.com (CC0). *Ultimate Modular Sci-Fi*,
  *Toon Shooter / City* packs, and the *Vehicles* packs have trucks and
  industrial buildings; many include `.glb`.
- **Poly Haven** — https://polyhaven.com/models (CC0). Realistic props (crates,
  pallets, containers) as glTF; usually heavier, so pick a low LOD / 1k textures.

Recommended mapping: factory → Kenney *City Kit (Industrial)* building,
warehouse → a Kenney industrial warehouse/hangar, store → Kenney *City Kit
(Commercial)* shop, truck → Kenney *Car Kit* `truck.glb` or a Quaternius
vehicle, crate → Kenney or Poly Haven wooden crate.

## Checking a model

Convert/inspect with <https://gltf.report> or `npx gltfjsx model.glb --transform`
(to shrink textures). If a file is present but looks wrong, the browser console
shows `Model failed to load; using placeholder` for corrupt files.
