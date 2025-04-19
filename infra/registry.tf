# Artifact Registry repository for storing container images
resource "google_artifact_registry_repository" "repository" {
  depends_on = [google_project_service.apis["artifactregistry.googleapis.com"]]
  
  provider      = google-beta
  location      = var.artifact_registry_location
  repository_id = var.artifact_registry_id
  format        = var.artifact_registry_format
  description   = "Docker repository for AI Ecosystem services"
  
  labels = {
    environment = "production"
    app         = "ai-ecosystem"
  }
}

# IAM policy to allow Cloud Build to push to Artifact Registry
resource "google_artifact_registry_repository_iam_member" "cloudbuild_push" {
  provider   = google-beta
  location   = google_artifact_registry_repository.repository.location
  repository = google_artifact_registry_repository.repository.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${var.project_id}@cloudbuild.gserviceaccount.com"
}
