import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'
import { probeModels } from './scene/models/ModelRegistry'

// Finds which .glb files are present (and preloads them); everything falls back to placeholders.
void probeModels()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
