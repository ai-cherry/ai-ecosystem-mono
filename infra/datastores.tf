# Redis instance for caching and message queuing
resource "google_redis_instance" "cache" {
  depends_on = [google_project_service.apis["redis.googleapis.com"]]
  
  name           = "ai-ecosystem-cache"
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_size_gb
  region         = var.region
  
  # Location ID for zonal resources
  location_id    = var.zone
  
  # Redis version
  redis_version  = "REDIS_6_X"
  
  # Enable AUTH for Redis
  auth_enabled = true
  
  # Use default VPC network
  authorized_network = var.network_name
  
  # Set display name for better organization
  display_name = "AI Ecosystem Redis Cache"
  
  # Enable connection via private services access
  connect_mode = "PRIVATE_SERVICE_ACCESS"
  
  # Labels for resource management
  labels = {
    environment = "production"
    app         = "ai-ecosystem"
  }
  
  # Maintenance policy - perform during quiet hours
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 2
        minutes = 0
      }
    }
  }
}

# Output the generated Redis AUTH string to Secret Manager
resource "google_secret_manager_secret" "redis_auth" {
  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
  
  secret_id = "redis-auth"
  
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

# Firestore is a serverless NoSQL database that doesn't need explicit provisioning 
# beyond enabling the service. It's already enabled in the google_project_service resource.
# We could create Firestore indexes in the future if needed.
