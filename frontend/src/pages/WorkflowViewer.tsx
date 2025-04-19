import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from 'react-query';
import { workflowService } from '../services/api';
import { WorkflowStatusResponse } from '../types';
import CodeMirror from '@uiw/react-codemirror';
import { json as jsonLanguage } from '@codemirror/lang-json';

const WorkflowViewer = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [logs, setLogs] = useState<string[]>([]);
  
  // Fetch workflow status with auto-refresh
  const { 
    data: workflow, 
    isLoading, 
    error,
    isError
  } = useQuery<WorkflowStatusResponse>(
    ['workflow', id],
    () => workflowService.getWorkflowStatus(id!),
    {
      enabled: !!id,
      refetchInterval: (data) => {
        // Stop polling if completed or failed
        return ['COMPLETED', 'FAILED', 'CANCELED', 'TERMINATED'].includes(data?.status || '')
          ? false
          : 3000;
      },
      onSuccess: (data) => {
        // Add a log entry when status changes
        if (data) {
          setLogs(prev => [
            ...prev, 
            `[${new Date().toLocaleTimeString()}] Workflow status: ${data.status}`
          ]);
          
          // If we have a result, add it to logs
          if (data.result && data.status === 'COMPLETED') {
            setLogs(prev => [
              ...prev, 
              `[${new Date().toLocaleTimeString()}] Workflow completed with result:`
            ]);
          }
        }
      }
    }
  );

  useEffect(() => {
    // Initialize logs when component mounts
    setLogs([`[${new Date().toLocaleTimeString()}] Fetching workflow ${id}...`]);
  }, [id]);

  // Format JSON for display
  const formatJSON = (obj: any) => {
    try {
      return JSON.stringify(obj, null, 2);
    } catch (e) {
      return JSON.stringify({ error: 'Unable to format JSON' });
    }
  };

  // Determine status color
  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'failed':
      case 'canceled':
      case 'terminated':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'running':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="flex items-center mb-6">
        <button
          onClick={() => navigate(-1)}
          className="mr-4 p-2 rounded-full hover:bg-gray-200"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Workflow Details</h1>
      </div>

      {isLoading ? (
        <div className="flex justify-center p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : isError ? (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-6">
          <strong className="font-bold">Error:</strong>
          <span className="block sm:inline"> Failed to load workflow details.</span>
        </div>
      ) : workflow ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Workflow Info */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <div className="mb-4 flex justify-between items-center">
                <h2 className="text-lg font-medium">Workflow Information</h2>
                <span 
                  className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(workflow.status)}`}
                >
                  {workflow.status}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Workflow ID</h3>
                  <p className="mt-1 text-sm text-gray-900">{workflow.workflow_id}</p>
                </div>
                {workflow.run_id && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Run ID</h3>
                    <p className="mt-1 text-sm text-gray-900">{workflow.run_id}</p>
                  </div>
                )}
                {workflow.created_at && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Created At</h3>
                    <p className="mt-1 text-sm text-gray-900">
                      {new Date(workflow.created_at).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>

              {workflow.result && (
                <div className="mt-6">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">Result</h3>
                  <div className="border rounded-md overflow-hidden">
                    <CodeMirror
                      value={formatJSON(workflow.result)}
                      height="200px"
                      extensions={[jsonLanguage()]}
                      editable={false}
                      theme="light"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Logs Console */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-md p-6 h-full">
              <h2 className="text-lg font-medium mb-4">Workflow Logs</h2>
              <div className="bg-gray-900 rounded-md p-4 h-64 overflow-y-auto">
                {logs.map((log, index) => (
                  <div key={index} className="text-white font-mono text-sm mb-1">
                    {log}
                  </div>
                ))}

                {workflow?.result && (
                  <div className="text-green-400 font-mono text-sm whitespace-pre-wrap mt-2">
                    {formatJSON(workflow.result)}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center text-gray-500 p-8">
          No workflow found with ID: {id}
        </div>
      )}
    </div>
  );
};

export default WorkflowViewer;
