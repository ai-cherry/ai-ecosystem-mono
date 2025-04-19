# AI Ecosystem Admin Dashboard

A React-based administration dashboard for the AI Ecosystem platform. This dashboard provides interfaces for managing agents, monitoring workflows, and configuring the system.

## Features

- **Workflow Monitoring**: Track and visualize the status of AI workflows
- **Agent Builder**: Create and configure AI agents with a form-based interface
- **Live Workflow Viewer**: View real-time workflow execution details and logs
- **One-click Agent Deployment**: Deploy agents directly to Codespaces

## Getting Started

### Prerequisites

- Node.js 16+
- npm or pnpm

### Installation

```bash
# Install dependencies
npm install
# or
pnpm install
```

### Development

```bash
# Start development server
npm run dev
# or
pnpm dev
```

The dashboard will be available at http://localhost:3000

### Building for Production

```bash
# Build the application
npm run build
# or
pnpm build
```

## Architecture

The dashboard connects to the Orchestrator API to manage workflows and agents:

- `/api/v1/async/process`: Start new workflows
- `/api/v1/async/workflow/{id}`: Get workflow status and results
- `/api/v1/agents`: Manage agent configurations

## Technologies Used

- React 18
- TypeScript
- Tailwind CSS
- React Router
- React Query
- Vite
- Axios
