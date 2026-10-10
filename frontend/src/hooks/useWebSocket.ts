import { useGameStore } from '../store/gameStore'
import type { ClientCommand, ServerMessage } from '../types/sim'

// One shared socket for the whole app (single-player, local backend).
let socket: WebSocket | null = null
let wantOpen = false
let retryTimer: ReturnType<typeof setTimeout> | undefined
let onMessage: ((msg: ServerMessage) => void) | null = null

export function setMessageHandler(handler: typeof onMessage) {
  onMessage = handler
}

export function connectSocket() {
  wantOpen = true
  if (socket && socket.readyState <= WebSocket.OPEN) return
  const { setConnection } = useGameStore.getState()
  setConnection('connecting')

  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${location.host}/ws/sim`)
  socket = ws

  ws.onopen = () => setConnection('open')
  ws.onmessage = (event) => {
    onMessage?.(JSON.parse(event.data) as ServerMessage)
  }
  ws.onclose = () => {
    if (socket === ws) socket = null
    setConnection('closed')
    if (wantOpen) retryTimer = setTimeout(connectSocket, 1000)
  }
}

export function closeSocket() {
  wantOpen = false
  clearTimeout(retryTimer)
  socket?.close()
  socket = null
  useGameStore.getState().setConnection('closed')
}

export function sendCommand(command: ClientCommand): boolean {
  if (!socket || socket.readyState !== WebSocket.OPEN) return false
  socket.send(JSON.stringify(command))
  return true
}
