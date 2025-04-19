# Cloud Run service for the orchestrator
resource "google_cloud_run_service" "orchestrator" {
  depends_on = [
    google_project_service.apis["run.googleapis.com"],
    google_vpc_access_connector.connector,
    google_redis_instance.cache
  ]
  
  name     = var.orchestrator_service_name
  location = var.region
  
  template {
    spec {
      service_account_name = google_service_account.orchestrator_sa.email
      
      containers {
        image = local.container_image
        
        resources {
          limits = {
            cpu    = var.orchestrator_cpu_limit
            memory = var.orchestrator_memory_limit
          }
        }
        
        # Environment variables for the orchestrator
        env {
          name  = "FIRESTORE_PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name  = "REDIS_URL"
          value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
        }
        
        # Reference to Secret Manager for sensitive data
        env {
          name = "REDIS_PASSWORD"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.redis_auth.secret_id
              key  = "latest"
            }
          }
        }
        
        env {
          name = "PINECONE_API_KEY"
          value_from {
            secret_key_ref {
              name = "pinecone-api-key"
              key  = "latest"
            }
          }
        }
        
        env {
          name = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = "openai-api-key"
              key  = "latest"
            }
          }
        }
        
        env {
          name  = "PINECONE_ENVIRONMENT"
          value = var.pinecone_environment
        }
        
        env {
          name  = "PINECONE_INDEX_NAME"
          value = "${var.project_id}-vectors"
        }
      }
      
      # Set container concurrency and timeout 
      container_concurrency = var.orchestrator_concurrency
      timeout_seconds = 300
    }
    
    metadata {
      annotations = {
        # Use VPC Connector for private networking
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector.name
        
        # Only send egress traffic to VPC and built-in load balancer
        "run.googleapis.com/vpc-access-egress" = "private-ranges-only"
        
        # CPU always allocated to improve startup times
        "run.googleapis.com/cpu-throttling" = "false"
        
        # Set minimum instances to 1 to prevent cold starts for critical service
        "autoscaling.knative.dev/minScale" = "1"
        
        # Set maximum instances to control costs
        "autoscaling.knative.dev/maxScale" = "10"
      }
    }
  }
  
  # Auto-generate revision name
  autogenerate_revision_name = true
  
  # Traffic 100% to latest revision
  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Allow unauthenticated access to the service
resource "google_cloud_run_service_iam_member" "public" {
  location = google_cloud_run_service.orchestrator.location
  service  = google_cloud_run_service.orchestrator.name
  role     = "roles/run.invoker"
  member   = "allUsers"  # In production, replace with specific identities
}

# Secrets for external API keys
resource "google_secret_manager_secret" "pinecone_api_key" {
  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
  
  secret_id = "pinecone-api-key"
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
  
  labels = {
    environment = "production"
    app         = "ai-ecosystem"
  }
}

resource "google_secret_manager_secret_version" "pinecone_api_key_version" {
  secret      = google_secret_manager_secret.pinecone_api_key.id
  secret_data = var.pinecone_api_key
}

resource "google_secret_manager_secret" "openai_api_key" {
  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
  
  secret_id = "openai-api-key"
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
  
  labels = {
    environment = "production"
    app         = "ai-ecosystem"
  }
}

resource "google_secret_manager_secret_version" "openai_api_key_version" {
  secret      = google_secret_manager_secret.openai_api_key.id
  secret_data = var.openai_api_key
}

# Binding to allow orchestrator SA to access the secrets
resource "google_secret_manager_secret_iam_member" "orchestrator_pinecone_secret" {
  secret_id = google_secret_manager_secret.pinecone_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.orchestrator_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "orchestrator_openai_secret" {
  secret_id = google_secret_manager_secret.openai_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.orchestrator_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "orchestrator_redis_secret" {
  secret_id = google_secret_manager_secret.redis_auth.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.orchestrator_sa.email}"
}
