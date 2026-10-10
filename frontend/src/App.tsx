import { useGameLoop } from './hooks/useGameLoop'
import { SupplyChainWorld } from './scene/SupplyChainWorld'
import { useGameStore } from './store/gameStore'
import { HistoryPanel } from './ui/HistoryPanel'
import { EditBanner } from './ui/EditBanner'
import { EditPanel } from './ui/EditPanel'
import { EditToolbar } from './ui/EditToolbar'
import { HUD } from './ui/HUD'
import { MilestoneBanner } from './ui/MilestoneBanner'
import { NodeInspector } from './ui/NodeInspector'
import { ResultsOverlay } from './ui/ResultsOverlay'
import { RunSettingsModal } from './ui/RunSettingsModal'
import { ScenarioBuilder } from './ui/ScenarioBuilder'
import { ToastStack } from './ui/ToastStack'

export default function App() {
  useGameLoop()
  const phase = useGameStore((s) => s.currentPhase)

  // The 3D canvas stays mounted behind the scenario picker: tearing it down with
  // drei <Html> labels inside throws a DOM error, and re-creating WebGL is wasteful.
  return (
    <div className="game">
      <SupplyChainWorld />
      {phase === 'setup' && (
        <div className="setup-screen">
          <ScenarioBuilder />
        </div>
      )}
      {phase === 'setup' ? null : phase === 'edit' ? (
        <>
          <EditBanner />
          <EditToolbar />
          <EditPanel />
          <RunSettingsModal />
        </>
      ) : (
        <>
          <HUD />
          <NodeInspector />
          <HistoryPanel />
          <MilestoneBanner />
          <ResultsOverlay />
        </>
      )}
      <ToastStack />
    </div>
  )
}
