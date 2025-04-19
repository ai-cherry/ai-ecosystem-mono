import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { workflowService } from '../services/api';
import { WorkflowStatusResponse } from '../types';

const Dashboard = () => {
  const [newWorkflowText, setNewWorkflowText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  
  // Fetch all workflows
  const { data: workflows, isLoading, error, refetch } = useQuery<WorkflowStatusResponse[]>(
    'workflows',
    async () => {
      try {
        return await workflowService.getAllWorkflows();
      } catch (err) {
        // If the endpoint doesn't exist yet, return mock data
        console.warn('Using mock data for workflows');
        return mockWorkflows;
      }
    },
    {
      refetchInterval: 5000, // Refetch every 5 seconds
    }
  );

  // Handle workflow submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newWorkflowText.trim()) return;
    
    setSubmitting(true);
    try {
      await workflowService.startWorkflow({
        data: newWorkflowText,
      });
      setNewWorkflowText('');
      refetch(); // Refresh the list
    } catch (error) {
      console.error('Failed to start workflow:', error);
    } finally {
      setSubmitting(false);
    }
  };

  // Render status badge with appropriate color
  const StatusBadge = ({ status }: { status: string }) => {
    let color = '';
    
    switch (status.toLowerCase()) {
      case 'completed':
        color = 'bg-green-100 text-green-800';
        break;
      case 'failed':
        color = 'bg-red-100 text-red-800';
        break;
      case 'running':
        color = 'bg-blue-100 text-blue-800';
        break;
      default:
        color = 'bg-gray-100 text-gray-800';
    }
    
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${color}`}>
        {status}
      </span>
    );
  };

  // Format timestamp
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Workflows Dashboard</h1>
        <Link 
          to="/agent-builder" 
          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
        >
          Create New Agent
        </Link>
      </div>
      
      {/* New Workflow Form */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-lg font-medium mb-4">Start New Workflow</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="workflowText" className="block text-sm font-medium text-gray-700 mb-1">
              Text to Process
            </label>
            <textarea
              id="workflowText"
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              placeholder="Enter text to process..."
              value={newWorkflowText}
              onChange={(e) => setNewWorkflowText(e.target.value)}
              disabled={submitting}
            />
          </div>
          <button
            type="submit"
            disabled={submitting || !newWorkflowText.trim()}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Starting...' : 'Start Workflow'}
          </button>
        </form>
      </div>
      
      {/* Workflows List */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-lg font-medium mb-4">Recent Workflows</h2>
        
        {isLoading ? (
          <div className="flex justify-center p-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : error ? (
          <div className="text-center text-red-500 p-4">
            Error loading workflows
          </div>
        ) : workflows && workflows.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Workflow ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {workflows.map((workflow) => (
                  <tr key={workflow.workflow_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {workflow.workflow_id.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <StatusBadge status={workflow.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {workflow.created_at ? formatTime(workflow.created_at) : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <Link
                        to={`/workflow/${workflow.workflow_id}`}
                        className="text-primary-600 hover:text-primary-900 mr-4"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center text-gray-500 p-8">
            No workflows found. Start one above!
          </div>
        )}
      </div>
    </div>
  );
};

// Mock data for development
const mockWorkflows: WorkflowStatusResponse[] = [
  {
    workflow_id: 'workflow-12345678',
    status: 'COMPLETED',
    result: { status: 'completed', result: 'HELLO WORLD' },
    created_at: new Date().toISOString(),
  },
  {
    workflow_id: 'workflow-23456789',
    status: 'RUNNING',
    created_at: new Date(Date.now() - 5 * 60000).toISOString(),
  },
  {
    workflow_id: 'workflow-34567890',
    status: 'FAILED',
    result: { status: 'failed', error: 'Process timeout' },
    created_at: new Date(Date.now() - 30 * 60000).toISOString(),
  },
];

export default Dashboard;
