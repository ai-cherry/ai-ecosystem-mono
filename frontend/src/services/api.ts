import axios from 'axios';
import { WorkflowRequest, WorkflowResponse, WorkflowStatusResponse, AgentConfig } from '../types';

const API_URL = '/api/v1/async';
const API_AGENTS_URL = '/api/v1/agents';

// Create an axios instance
const apiClient = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Workflow API services
export const workflowService = {
  // Start a new workflow
  startWorkflow: async (request: WorkflowRequest): Promise<WorkflowResponse> => {
    try {
      const response = await apiClient.post(`${API_URL}/process`, request);
      return response.data;
    } catch (error) {
      console.error('Error starting workflow:', error);
      throw error;
    }
  },

  // Get workflow status and result
  getWorkflowStatus: async (workflowId: string): Promise<WorkflowStatusResponse> => {
    try {
      const response = await apiClient.get(`${API_URL}/workflow/${workflowId}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching workflow status for ${workflowId}:`, error);
      throw error;
    }
  },

  // Get all workflows
  getAllWorkflows: async (): Promise<WorkflowStatusResponse[]> => {
    try {
      const response = await apiClient.get(`${API_URL}/workflows`);
      return response.data;
    } catch (error) {
      console.error('Error fetching all workflows:', error);
      throw error;
    }
  }
};

// Agent API services
export const agentService = {
  // Get all agent configurations
  getAllAgents: async (): Promise<AgentConfig[]> => {
    try {
      const response = await apiClient.get(`${API_AGENTS_URL}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching agents:', error);
      throw error;
    }
  },

  // Get a specific agent config
  getAgent: async (agentId: string): Promise<AgentConfig> => {
    try {
      const response = await apiClient.get(`${API_AGENTS_URL}/${agentId}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching agent ${agentId}:`, error);
      throw error;
    }
  },

  // Create a new agent
  createAgent: async (agentConfig: AgentConfig): Promise<AgentConfig> => {
    try {
      const response = await apiClient.post(`${API_AGENTS_URL}`, agentConfig);
      return response.data;
    } catch (error) {
      console.error('Error creating agent:', error);
      throw error;
    }
  },

  // Update an existing agent
  updateAgent: async (agentId: string, agentConfig: AgentConfig): Promise<AgentConfig> => {
    try {
      const response = await apiClient.put(`${API_AGENTS_URL}/${agentId}`, agentConfig);
      return response.data;
    } catch (error) {
      console.error(`Error updating agent ${agentId}:`, error);
      throw error;
    }
  },

  // Delete an agent
  deleteAgent: async (agentId: string): Promise<void> => {
    try {
      await apiClient.delete(`${API_AGENTS_URL}/${agentId}`);
    } catch (error) {
      console.error(`Error deleting agent ${agentId}:`, error);
      throw error;
    }
  },

  // Deploy an agent to Codespaces
  deployAgent: async (agentId: string): Promise<any> => {
    try {
      const response = await apiClient.post(`${API_AGENTS_URL}/${agentId}/deploy`);
      return response.data;
    } catch (error) {
      console.error(`Error deploying agent ${agentId}:`, error);
      throw error;
    }
  }
};

// Tools and Memory backends API
export const toolsService = {
  // Get available tools
  getAvailableTools: async (): Promise<any[]> => {
    try {
      const response = await apiClient.get(`${API_AGENTS_URL}/tools`);
      return response.data;
    } catch (error) {
      console.error('Error fetching available tools:', error);
      throw error;
    }
  },

  // Get available memory backends
  getMemoryBackends: async (): Promise<any[]> => {
    try {
      const response = await apiClient.get(`${API_AGENTS_URL}/memory-backends`);
      return response.data;
    } catch (error) {
      console.error('Error fetching memory backends:', error);
      throw error;
    }
  }
};

export default {
  workflowService,
  agentService,
  toolsService
};
