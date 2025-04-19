# Output values for the infrastructure

# Cloud Run service URL
output "orchestrator_url" {
  description = "The URL of the deployed orchestrator service"
  value       = google_cloud_run_service.orchestrator.status[0].url
}

# Redis connection information
output "redis_host" {
  description = "The hostname of the Redis instance"
  value       = google_redis_instance.cache.host
}

output "redis_port" {
  description = "The port of the Redis instance"
  value       = google_redis_instance.cache.port
}

# VPC Connector information
output "vpc_connector" {
  description = "The VPC connector for serverless services"
  value       = google_vpc_access_connector.connector.id
}

# Artifact Registry Repository
output "artifact_repository" {
  description = "The Artifact Registry repository for container images"
  value       = "https://${var.artifact_registry_location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repository.repository_id}"
}

# Service Account email
output "orchestrator_service_account" {
  description = "The email of the service account for the orchestrator"
  value       = google_service_account.orchestrator_sa.email
}

# Secret Manager secret names
output "secrets" {
  description = "The names of the Secret Manager secrets"
  value = {
    "redis_auth"      = google_secret_manager_secret.redis_auth.name
    "pinecone_api_key" = google_secret_manager_secret.pinecone_api_key.name
    "openai_api_key"   = google_secret_manager_secret.openai_api_key.name
  }
}

# Pinecone settings
output "pinecone_environment" {
  description = "The Pinecone environment"
  value       = var.pinecone_environment
}

output "pinecone_index_name" {
  description = "The Pinecone index name"
  value       = "${var.project_id}-vectors"
}

# Instructions
output "deployment_instructions" {
  description = "Next steps after Terraform deployment"
  value       = <<-EOT
    🚀 AI Ecosystem Infrastructure Successfully Deployed 🚀
    
    Cloud Run Orchestrator URL: ${google_cloud_run_service.orchestrator.status[0].url}
    
    Next Steps:
    1. Set up CI/CD pipelines to build and deploy the orchestrator service
       - Use the Artifact Repository: ${var.artifact_registry_location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repository.repository_id}
    
    2. Update your .env file with the following configuration:
       - REDIS_URL=redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}
       - FIRESTORE_PROJECT_ID=${var.project_id}
       - PINECONE_ENVIRONMENT=${var.pinecone_environment}
       - PINECONE_INDEX_NAME=${var.project_id}-vectors
    
    3. Access the Secret Manager to retrieve sensitive credentials:
       - Redis password: ${google_secret_manager_secret.redis_auth.name}
       - Pinecone API key: ${google_secret_manager_secret.pinecone_api_key.name}
       - OpenAI API key: ${google_secret_manager_secret.openai_api_key.name}
    
    Remember to set up CI/CD to automatically build and deploy the orchestrator
    service whenever changes are pushed to the repository.
  EOT
}
