export interface Workspace {
  id: string;
  name: string;
  root: string;
}
export interface Session {
  id: string;
  title: string;
  workspace_id: string;
  created_at: string;
}
export interface Change {
  path: string;
  before: string | null;
  after: string | null;
  diff: string;
  encoding?: 'base64';
  mime_type?: 'image/png';
}
export interface Patch {
  id: string;
  task_id: string;
  status: string;
  changes: Change[];
}
export interface Task {
  id: string;
  session_id: string;
  prompt: string;
  skill?: 'annotate-project-zh' | 'analyze-project-zh' | null;
  status: string;
  result: string;
  steps: number;
  selected_file?: string | null;
  test_argv?: string[];
  patches?: Patch[];
}
export interface ModelSettings {
  connection_id: string | null;
  connection_name: string;
  model: string;
  base_url: string;
  has_api_key: boolean;
  key_storage: string;
  max_steps: number;
}
export interface SavedConnection extends Omit<ModelSettings, 'connection_id' | 'connection_name'> {
  id: string;
  name: string;
}
export interface TaskEvent {
  id?: number;
  task_id: string;
  kind: string;
  data: {
    message?: string;
    text?: string;
    step?: number;
    action?: string;
    patch_id?: string;
    exit_code?: number | null;
  };
}
export interface Bridge {
  bootstrap(): Promise<{ version: string; settings: ModelSettings; workspaces: Workspace[] }>;
  openWorkspace(): Promise<Workspace | null>;
  openDroppedProject(file: File): Promise<{ workspace: Workspace; selectedFile: string | null }>;
  windowState(): Promise<{ maximized: boolean }>;
  windowControl(action: 'minimize' | 'maximize' | 'close'): Promise<{ maximized: boolean }>;
  request<T>(method: string, path: string, body?: unknown): Promise<T>;
  watchTask(id: string, after?: number): Promise<void>;
  unwatchTask(id: string): Promise<void>;
  onOpenSettings(listener: () => void): () => void;
  onEvent(listener: (event: TaskEvent) => void): () => void;
}
declare global {
  interface Window {
    codeAssistant: Bridge;
  }
}
