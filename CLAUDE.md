# ChainSim 3D — Supply Chain Management Game

## What This Project Is

A 3D interactive supply chain management game built on top of the `chainsim` Python simulation library. The player acts as a supply chain manager: building networks, setting policies, and watching the simulation play out in a 3D world where warehouses fill up, trucks move along routes, and disruptions hit visually.

The existing `chainsim` library (in `supply-chain-sim/`) handles ALL simulation logic. This project is a new game-like frontend that replaces the old Streamlit dashboard. No business logic in the UI — the frontend only renders state and captures player input.

## Architecture

```
chainsim-game/          # NEW — this project
├── frontend/           # Vite + React 19 + TypeScript
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── store/          # Zustand stores (game state, sim state)
│   │   ├── scene/          # R3F 3D scene components
│   │   │   ├── SupplyChainWorld.tsx   # Main 3D scene
│   │   │   ├── nodes/                 # WarehouseNode, FactoryNode, RetailerNode
│   │   │   ├── edges/                 # TransportEdge (animated flow lines / trucks)
│   │   │   ├── effects/              # Disruption visuals, demand pulses
│   │   │   └── environment/          # Ground plane, lighting, sky
│   │   ├── ui/             # HTML overlay panels (React DOM, not 3D)
│   │   │   ├── HUD.tsx               # Top bar: period counter, total cost, controls
│   │   │   ├── NodeInspector.tsx      # Side panel when clicking a node
│   │   │   ├── PolicySelector.tsx     # Change replenishment policy
│   │   │   ├── ScenarioBuilder.tsx    # Initial setup screen
│   │   │   └── ResultsOverlay.tsx     # End-of-run summary
│   │   ├── hooks/          # useSimulation, useGameLoop, useWebSocket
│   │   └── types/          # TypeScript types mirroring chainsim models
│   ├── public/
│   │   └── models/         # .glb 3D model files (not in git, downloaded separately)
│   └── package.json
│
├── backend/            # FastAPI + WebSocket bridge to chainsim
│   ├── main.py         # FastAPI app, WebSocket endpoint
│   ├── sim_bridge.py   # Wraps chainsim engine for the game
│   ├── schemas.py      # Pydantic models for WS messages
│   └── requirements.txt
│
└── CLAUDE.md           # This file
```

## Tech Stack

### Frontend
- **React 19** + TypeScript + Vite
- **React Three Fiber v9** (`@react-three/fiber`) — React renderer for Three.js
- **Drei** (`@react-three/drei`) — R3F helpers: OrbitControls, Html overlays, Text, useGLTF, Environment, Instances
- **Zustand** — state management (game state, simulation state, UI state)
- **gltfjsx** — CLI tool to convert .glb models into React components (`npx gltfjsx model.glb --transform --typescript`)

### Backend
- **FastAPI** with WebSocket support
- **chainsim** library (existing): `chainsim.core`, `chainsim.metrics`, `chainsim.scenarios`
- Python 3.11, uvicorn

### Communication
- WebSocket for real-time sim state streaming (backend → frontend)
- REST endpoints for scenario setup, policy changes (frontend → backend)

## Key Design Principles

1. **Placeholder-first**: Start with colored boxes/spheres for nodes. Swap in real .glb models later. Don't block on assets.
2. **Game state in Zustand, sim state from backend**: The frontend Zustand store holds camera position, selected node, UI panels open/closed, and a mirror of the latest sim state received via WebSocket. The backend is the source of truth for simulation.
3. **No business logic in frontend**: The frontend never calculates inventory, costs, or metrics. It receives them from the backend and renders them.
4. **Drei Html for UI overlays on 3D**: Inventory counts, node names, and KPI badges float above 3D nodes using `<Html>` from drei. Side panels and HUD are regular React DOM components outside the Canvas.
5. **Isometric-ish camera**: Default to a fixed-angle top-down view (like a tycoon game), with OrbitControls so the player can rotate/zoom if they want.

## chainsim API Surface (what the backend wraps)

The chainsim library provides:
- `SupplyChainNetwork` — graph of nodes and edges
- `SimulationEngine` — `begin()`, `step()`, `finish()` to run period-by-period
- `DemandGenerator` variants — Stationary, Seasonal, Trend
- `ReplenishmentPolicy` variants — OrderUpTo, (s,S), (R,Q), BaseStock
- `DisruptionEvent` — NodeOutage, CapacityReduction, LeadTimeShock, DemandShock
- Metrics: `per_node_kpis()`, `compare_scenarios()`, fill_rate, service_level, bullwhip_ratio, total_cost, total_waste
- Pre-built scenarios: Retail Replenishment, Pharma Cold Chain, Manufacturing JIT, Global Commodity Flow

## Game Flow

1. **Setup phase**: Player picks a pre-built scenario or builds a custom chain. 3D world shows the network being assembled.
2. **Play phase**: Player hits "Start". Each period ticks (auto or manual step). 3D world updates: inventory boxes stack/unstack in warehouses, trucks animate between nodes, demand pulses glow at retailers. Player can pause, change policies, and resume.
3. **Event phase**: Disruptions appear as visual effects (red flash, warning icon). Player reacts by adjusting policies.
4. **Results phase**: Run ends. Camera pulls back to show the full chain. KPI summary overlays appear. Player can compare with previous runs.

## Visual Language (placeholder phase)

- **Supplier/Factory**: Blue box
- **Distribution Center**: Yellow box
- **Retailer**: Green box
- **Edges**: Animated dashed lines showing flow direction
- **Inventory**: Small cubes stacking inside/on top of nodes (count = on_hand / scale_factor)
- **Demand**: Pulsing circle at retailer nodes
- **Disruption**: Red glow / shake on affected node
- **Trucks** (later): Small box moving along edge path

## Commands

```bash
# Frontend
cd frontend && npm install && npm run dev    # localhost:5173

# Backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000

# Convert a 3D model to R3F component
npx gltfjsx public/models/warehouse.glb --transform --typescript --output src/scene/nodes/Warehouse.tsx
```

## What NOT to Do

- Don't use Streamlit, Plotly, or any of the old dashboard code
- Don't put simulation logic in the frontend
- Don't require 3D model files to exist for the app to run (use placeholder geometry)
- Don't use CSS frameworks — keep styling minimal, game-like (dark background, glowing accents)
- Don't over-engineer the first version — get boxes moving on screen first