import { createContext, useContext } from 'react'
import type { Mode, Page, Settings, Workspace } from './types'

export interface WorkbenchContext {
  workspace: Workspace | null
  settings: Settings | null
  mode: Mode
  setMode: (mode: Mode) => void
  busy: string
  navigate: (page: Page) => void
  updateWorkspace: (workspace: Workspace) => void
  run: (task: () => Promise<void>, label: string) => Promise<void>
  startInterview: (
    focus?: 'all' | 'weak',
    count?: number,
    sourceSessionId?: string,
    maxTopicTurns?: number,
    demonstration?: boolean,
  ) => void
  setUnsaved: (value: boolean) => void
  sessionId: string
  setSessionId: (id: string) => void
  refreshSettings: () => Promise<void>
}
export const Workbench = createContext<WorkbenchContext | null>(null)
export function useWorkbench() {
  const context = useContext(Workbench)
  if (!context) throw new Error('Workbench provider missing')
  return context
}
