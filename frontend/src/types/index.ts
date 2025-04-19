// Workflow types
export interface WorkflowRequest {
  data: string;
  workflow_id?: string;
}

export interface WorkflowResponse {
  workflow_id: string;
  run_id: string;
}

export interface WorkflowStatusResponse {
  workflow_id: string;
  status: string;
  result?: any;
  created_at?: string;
}

// Agent types
export interface AgentConfig {
  id?: string;
  name: string;
  description?: string;
  persona: string;
  tools: string[];
  memory_backend: string;
  created_at?: string;
  updated_at?: string;
}

export interface MemoryBackend {
  id: string;
  name: string;
  type: 'redis' | 'firestore' | 'vectorstore';
  config: Record<string, any>;
}

export interface Tool {
  id: string;
  name: string;
  description: string;
  parameters: Record<string, any>;
}
