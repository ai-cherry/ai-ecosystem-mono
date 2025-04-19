terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.0"
    }
  }
  required_version = ">= 1.0.0"
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Enable required GCP APIs
resource "google_project_service" "apis" {
  for_each = toset(var.required_apis)
  
  project = var.project_id
  service = each.value
  
  disable_on_destroy = false
}

# Local variable to use project ID in container image
locals {
  container_image = replace(var.orchestrator_container_image, "PROJECT_ID", var.project_id)
}
