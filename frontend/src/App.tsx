import { useGameLoop } from './hooks/useGameLoop'
import { SupplyChainWorld } from './scene/SupplyChainWorld'
import { useGameStore } from './store/gameStore'
import { HintBubble } from './ui/HintBubble'
import { HistoryPanel } from './ui/HistoryPanel'
import { HomeScreen } from './ui/HomeScreen'
import { LevelStart } from './ui/LevelStart'
import { CampaignMap } from './ui/CampaignMap'
import { CampaignResults } from './ui/CampaignResults'
import { EditBanner } from './ui/EditBanner'
import { EventCard } from './ui/EventCard'
import { EventLogPanel } from './ui/EventLogPanel'
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
  const view = useGameStore((s) => s.setupView)

  // The 3D canvas stays mounted behind the scenario picker: tearing it down with
  // drei <Html> labels inside throws a DOM error, and re-creating WebGL is wasteful.
  return (
    <div className="game">
      <SupplyChainWorld />
      {phase === 'setup' && (
        <div className="setup-screen">
          {view === 'home' && <HomeScreen />}
          {view === 'campaign' && <CampaignMap />}
          {view === 'levelStart' && <LevelStart />}
          {view === 'sandbox' && <ScenarioBuilder />}
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
          <EventLogPanel />
          <MilestoneBanner />
          <ResultsOverlay />
          <CampaignResults />
          <HintBubble />
          <EventCard />
        </>
      )}
      <ToastStack />
    </div>
  )
}
