import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { agentService, toolsService } from '../services/api';
import { AgentConfig, Tool, MemoryBackend } from '../types';
import CodeMirror from '@uiw/react-codemirror';
import { json as jsonLanguage } from '@codemirror/lang-json';

const AgentBuilder = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  
  // Form state
  const [agentConfig, setAgentConfig] = useState<AgentConfig>({
    name: '',
    description: '',
    persona: '',
    tools: [],
    memory_backend: ''
  });
  
  // UI state
  const [activeTab, setActiveTab] = useState<'config' | 'persona' | 'tools' | 'storage'>('config');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  
  // Fetch available tools
  const { 
    data: availableTools = [] as Tool[],
    isLoading: isLoadingTools,
  } = useQuery<Tool[]>(
    'tools',
    async () => {
      try {
        return await toolsService.getAvailableTools();
      } catch (err) {
        console.warn('Using mock tools data');
        return mockTools;
      }
    }
  );
  
  // Fetch available memory backends
  const { 
    data: memoryBackends = [] as MemoryBackend[],
    isLoading: isLoadingMemory 
  } = useQuery<MemoryBackend[]>(
    'memory-backends',
    async () => {
      try {
        return await toolsService.getMemoryBackends();
      } catch (err) {
        console.warn('Using mock memory backends data');
        return mockMemoryBackends;
      }
    }
  );
  
  // Create agent mutation
  const createAgentMutation = useMutation(
    (config: AgentConfig) => agentService.createAgent(config),
    {
      onSuccess: (data) => {
        setSuccessMessage(`Agent "${data.name}" created successfully!`);
        queryClient.invalidateQueries('agents');
        setTimeout(() => {
          navigate('/dashboard');
        }, 2000);
      },
      onError: (error: any) => {
        setErrorMessage(error?.message || 'Failed to create agent');
      },
      onSettled: () => {
        setIsSubmitting(false);
      }
    }
  );
  
  // Deploy agent mutation
  const deployAgentMutation = useMutation(
    (agentId: string) => agentService.deployAgent(agentId),
    {
      onSuccess: (data) => {
        setSuccessMessage('Agent deployed to Codespaces successfully!');
      },
      onError: (error: any) => {
        setErrorMessage(error?.message || 'Failed to deploy agent');
      },
      onSettled: () => {
        setIsSubmitting(false);
      }
    }
  );
  
  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate form
    if (!agentConfig.name.trim()) {
      setErrorMessage('Agent name is required');
      return;
    }
    
    if (!agentConfig.persona.trim()) {
      setErrorMessage('Agent persona is required');
      return;
    }
    
    if (agentConfig.tools.length === 0) {
      setErrorMessage('At least one tool must be selected');
      return;
    }
    
    if (!agentConfig.memory_backend) {
      setErrorMessage('Memory backend is required');
      return;
    }
    
    setIsSubmitting(true);
    setErrorMessage('');
    setSuccessMessage('');
    
    // Submit form
    createAgentMutation.mutate(agentConfig);
  };
  
  // Handle input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setAgentConfig(prev => ({ ...prev, [name]: value }));
  };
  
  // Handle tool selection
  const handleToolToggle = (toolId: string) => {
    setAgentConfig(prev => {
      if (prev.tools.includes(toolId)) {
        return { ...prev, tools: prev.tools.filter(id => id !== toolId) };
      } else {
        return { ...prev, tools: [...prev.tools, toolId] };
      }
    });
  };
  
  // Navigate between tabs
  const handleNext = () => {
    if (activeTab === 'config') setActiveTab('persona');
    else if (activeTab === 'persona') setActiveTab('tools');
    else if (activeTab === 'tools') setActiveTab('storage');
  };
  
  const handleBack = () => {
    if (activeTab === 'persona') setActiveTab('config');
    else if (activeTab === 'tools') setActiveTab('persona');
    else if (activeTab === 'storage') setActiveTab('tools');
  };
  
  return (
    <div className="container mx-auto px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Agent Builder</h1>
      </div>
      
      {/* Stepper */}
      <div className="mb-8">
        <div className="flex justify-between items-center">
          <div 
            className={`flex flex-col items-center ${activeTab === 'config' ? 'text-primary-600' : 'text-gray-500'}`}
            onClick={() => setActiveTab('config')}
          >
            <div className={`h-8 w-8 rounded-full flex items-center justify-center ${activeTab === 'config' ? 'bg-primary-100 text-primary-600' : 'bg-gray-100'}`}>
              1
            </div>
            <span className="mt-1 text-sm">Config</span>
          </div>
          <div className="flex-1 h-1 mx-2 bg-gray-200" />
          <div 
            className={`flex flex-col items-center ${activeTab === 'persona' ? 'text-primary-600' : 'text-gray-500'}`}
            onClick={() => setActiveTab('persona')}
          >
            <div className={`h-8 w-8 rounded-full flex items-center justify-center ${activeTab === 'persona' ? 'bg-primary-100 text-primary-600' : 'bg-gray-100'}`}>
              2
            </div>
            <span className="mt-1 text-sm">Persona</span>
          </div>
          <div className="flex-1 h-1 mx-2 bg-gray-200" />
          <div 
            className={`flex flex-col items-center ${activeTab === 'tools' ? 'text-primary-600' : 'text-gray-500'}`}
            onClick={() => setActiveTab('tools')}
          >
            <div className={`h-8 w-8 rounded-full flex items-center justify-center ${activeTab === 'tools' ? 'bg-primary-100 text-primary-600' : 'bg-gray-100'}`}>
              3
            </div>
            <span className="mt-1 text-sm">Tools</span>
          </div>
          <div className="flex-1 h-1 mx-2 bg-gray-200" />
          <div 
            className={`flex flex-col items-center ${activeTab === 'storage' ? 'text-primary-600' : 'text-gray-500'}`}
            onClick={() => setActiveTab('storage')}
          >
            <div className={`h-8 w-8 rounded-full flex items-center justify-center ${activeTab === 'storage' ? 'bg-primary-100 text-primary-600' : 'bg-gray-100'}`}>
              4
            </div>
            <span className="mt-1 text-sm">Storage</span>
          </div>
        </div>
      </div>

      {/* Success/Error Messages */}
      {successMessage && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mb-6">
          <span className="block sm:inline">{successMessage}</span>
        </div>
      )}
      
      {errorMessage && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-6">
          <span className="block sm:inline">{errorMessage}</span>
        </div>
      )}
      
      {/* Form */}
      <form onSubmit={handleSubmit}>
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          {/* Basic Configuration Tab */}
          {activeTab === 'config' && (
            <div>
              <h2 className="text-lg font-medium mb-4">Basic Configuration</h2>
              <div className="mb-4">
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Agent Name*
                </label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={agentConfig.name}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                  placeholder="Enter agent name"
                  required
                />
              </div>
              
              <div className="mb-4">
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  id="description"
                  name="description"
                  value={agentConfig.description}
                  onChange={handleInputChange}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                  placeholder="Describe the agent's purpose"
                />
              </div>
            </div>
          )}
          
          {/* Persona Editor Tab */}
          {activeTab === 'persona' && (
            <div>
              <h2 className="text-lg font-medium mb-4">Persona Editor</h2>
              <div className="mb-4">
                <label htmlFor="persona" className="block text-sm font-medium text-gray-700 mb-1">
                  Agent Persona*
                </label>
                <textarea
                  id="persona"
                  name="persona"
                  value={agentConfig.persona}
                  onChange={handleInputChange}
                  rows={12}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 font-mono"
                  placeholder="Define the agent's persona, capabilities, and behavior..."
                  required
                />
              </div>
              <div className="bg-gray-50 p-4 rounded-md">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Persona Tips</h3>
                <ul className="list-disc pl-5 text-sm text-gray-600">
                  <li>Be specific about the agent's expertise and knowledge areas</li>
                  <li>Define how the agent should interact with users</li>
                  <li>Include any constraints or limitations</li>
                  <li>Describe the agent's personality traits</li>
                </ul>
              </div>
            </div>
          )}
          
          {/* Tools Selection Tab */}
          {activeTab === 'tools' && (
            <div>
              <h2 className="text-lg font-medium mb-4">Select Tools</h2>
              
              {isLoadingTools ? (
                <div className="flex justify-center p-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                </div>
              ) : (
                <div className="space-y-3">
                  {availableTools.map(tool => (
                    <div key={tool.id} className="flex items-start p-3 border rounded-md hover:bg-gray-50">
                      <input
                        type="checkbox"
                        id={`tool-${tool.id}`}
                        checked={agentConfig.tools.includes(tool.id)}
                        onChange={() => handleToolToggle(tool.id)}
                        className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                      <label htmlFor={`tool-${tool.id}`} className="ml-3 flex-1 cursor-pointer">
                        <span className="block text-sm font-medium text-gray-700">{tool.name}</span>
                        <span className="block text-sm text-gray-500">{tool.description}</span>
                      </label>
                    </div>
                  ))}
                </div>
              )}
              
              {availableTools.length === 0 && !isLoadingTools && (
                <div className="text-center p-8 text-gray-500">
                  No tools available. Add tools to your AI ecosystem.
                </div>
              )}
            </div>
          )}
          
          {/* Storage Configuration Tab */}
          {activeTab === 'storage' && (
            <div>
              <h2 className="text-lg font-medium mb-4">Memory & Storage</h2>
              
              <div className="mb-6">
                <label htmlFor="memory_backend" className="block text-sm font-medium text-gray-700 mb-1">
                  Memory Backend*
                </label>
                
                {isLoadingMemory ? (
                  <div className="flex justify-center p-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {memoryBackends.map(memory => (
                      <div 
                        key={memory.id}
                        onClick={() => setAgentConfig(prev => ({ ...prev, memory_backend: memory.id }))}
                        className={`border rounded-lg p-4 cursor-pointer ${
                          agentConfig.memory_backend === memory.id
                            ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-500'
                            : 'hover:bg-gray-50'
                        }`}
                      >
                        <div className="font-medium">{memory.name}</div>
                        <div className="text-sm text-gray-500 mt-1">Type: {memory.type}</div>
                      </div>
                    ))}
                  </div>
                )}
                
                {memoryBackends.length === 0 && !isLoadingMemory && (
                  <div className="text-center p-4 text-gray-500 border rounded-md">
                    No memory backends available. Please configure one in settings.
                  </div>
                )}
              </div>
              
              <div className="mb-6">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Deployment Options</h3>
                <div className="flex space-x-4">
                  <div className="border rounded-lg p-4 flex-1 bg-gray-50">
                    <div className="font-medium">Store in Firestore</div>
                    <div className="text-sm text-gray-500 mt-1">Agent config will be stored in Cloud Firestore</div>
                  </div>
                  <div className="border rounded-lg p-4 flex-1 bg-gray-50">
                    <div className="font-medium">Store in GitHub</div>
                    <div className="text-sm text-gray-500 mt-1">Agent config will be saved as a GitHub repository</div>
                  </div>
                </div>
              </div>
              
              <div className="border-t pt-6">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Creating Agent...' : 'Create Agent'}
                </button>
              </div>
            </div>
          )}
          
          {/* Navigation Buttons */}
          {activeTab !== 'storage' && (
            <div className="mt-6 flex justify-between">
              {activeTab !== 'config' ? (
                <button
                  type="button"
                  onClick={handleBack}
                  className="px-4 py-2 border border-gray-300 bg-white text-gray-700 rounded-md hover:bg-gray-50"
                >
                  Back
                </button>
              ) : (
                <div></div>
              )}
              <button
                type="button"
                onClick={handleNext}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </form>
    </div>
  );
};

// Mock data for development
const mockTools: Tool[] = [
  {
    id: 'web-search',
    name: 'Web Search',
    description: 'Search the web for current information',
    parameters: { query: 'string' }
  },
  {
    id: 'code-executor',
    name: 'Code Executor',
    description: 'Execute code in a sandboxed environment',
    parameters: { language: 'string', code: 'string' }
  },
  {
    id: 'file-manager',
    name: 'File Manager',
    description: 'Read and write files on the system',
    parameters: { path: 'string', content: 'string' }
  },
  {
    id: 'api-client',
    name: 'API Client',
    description: 'Make HTTP requests to external APIs',
    parameters: { url: 'string', method: 'string', body: 'object' }
  }
];

const mockMemoryBackends: MemoryBackend[] = [
  {
    id: 'redis-memory',
    name: 'Redis Memory',
    type: 'redis',
    config: { host: 'localhost', port: 6379 }
  },
  {
    id: 'firestore-memory',
    name: 'Firestore Memory',
    type: 'firestore',
    config: { collection: 'agent-memory' }
  },
  {
    id: 'pinecone-memory',
    name: 'Pinecone Vectorstore',
    type: 'vectorstore',
    config: { index: 'agent-embeddings' }
  }
];

export default AgentBuilder;
