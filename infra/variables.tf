variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone for zonal resources"
  type        = string
  default     = "us-central1-a"
}

variable "orchestrator_service_name" {
  description = "Name of the orchestrator Cloud Run service"
  type        = string
  default     = "ai-orchestrator"
}

variable "orchestrator_container_image" {
  description = "Container image for the orchestrator service"
  type        = string
  default     = "gcr.io/PROJECT_ID/ai-orchestrator:latest"
}

variable "orchestrator_memory_limit" {
  description = "Memory limit for the orchestrator service"
  type        = string
  default     = "512Mi"
}

variable "orchestrator_cpu_limit" {
  description = "CPU limit for the orchestrator service"
  type        = string
  default     = "1000m"
}

variable "orchestrator_concurrency" {
  description = "Maximum number of concurrent requests per container"
  type        = number
  default     = 80
}

variable "redis_memory_size_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 1
}

variable "redis_tier" {
  description = "Redis tier (BASIC or STANDARD_HA)"
  type        = string
  default     = "BASIC"
}

variable "vpc_connector_name" {
  description = "Name of the VPC connector for serverless services"
  type        = string
  default     = "serverless-connector"
}

variable "vpc_connector_cidr" {
  description = "CIDR range for the VPC connector"
  type        = string
  default     = "10.8.0.0/28"
}

variable "network_name" {
  description = "Name of the VPC network"
  type        = string
  default     = "default"
}

variable "artifact_registry_id" {
  description = "ID for the Artifact Registry repository"
  type        = string
  default     = "ai-ecosystem"
}

variable "artifact_registry_location" {
  description = "Location for the Artifact Registry repository"
  type        = string
  default     = "us-central1"
}

variable "artifact_registry_format" {
  description = "Format for the Artifact Registry repository"
  type        = string
  default     = "DOCKER"
}

variable "service_account_name" {
  description = "Name of the service account for Cloud Run"
  type        = string
  default     = "ai-orchestrator-sa"
}

variable "pinecone_api_key" {
  description = "Pinecone API key for vector database"
  type        = string
  sensitive   = true
}

variable "pinecone_environment" {
  description = "Pinecone environment"
  type        = string
  default     = "us-west1-gcp"
}

variable "openai_api_key" {
  description = "OpenAI API key for embeddings and LLM"
  type        = string
  sensitive   = true
}

variable "required_apis" {
  description = "List of APIs to enable for the project"
  type        = list(string)
  default = [
    "run.googleapis.com",        # Cloud Run
    "artifactregistry.googleapis.com", # Artifact Registry
    "firestore.googleapis.com",  # Firestore
    "redis.googleapis.com",      # Redis (Memorystore)
    "vpcaccess.googleapis.com",  # VPC Access (for Serverless VPC Connector)
    "secretmanager.googleapis.com", # Secret Manager
    "compute.googleapis.com",    # Compute Engine (needed for VPC)
    "iam.googleapis.com",        # IAM
    "logging.googleapis.com",    # Cloud Logging
    "monitoring.googleapis.com"  # Cloud Monitoring
  ]
}
