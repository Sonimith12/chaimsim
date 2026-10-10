import { Component, type ReactNode } from 'react'

interface Props {
  fallback: ReactNode
  children: ReactNode
}

/** Renders `fallback` if anything below throws (e.g. a corrupt .glb). */
export class ErrorBoundary extends Component<Props, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: unknown) {
    console.warn('Model failed to load; using placeholder.', error)
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}
