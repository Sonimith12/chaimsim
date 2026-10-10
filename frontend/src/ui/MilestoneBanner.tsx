import { useGameStore } from '../store/gameStore'

export function MilestoneBanner() {
  const banner = useGameStore((s) => s.banner)
  if (!banner) return null
  // Keyed so each banner replays the fade-in/out animation.
  return (
    <div key={banner.id} className="milestone-banner">
      {banner.text}
    </div>
  )
}
