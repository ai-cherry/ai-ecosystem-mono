# VPC Connector for Cloud Run to access VPC resources like Redis
resource "google_vpc_access_connector" "connector" {
  depends_on = [google_project_service.apis["vpcaccess.googleapis.com"]]
  
  provider      = google-beta
  name          = var.vpc_connector_name
  region        = var.region
  network       = var.network_name
  ip_cidr_range = var.vpc_connector_cidr
  
  # Standard machine type for the connector
  machine_type = "e2-standard-4"
  
  # Min and max instances for the connector
  min_instances = 2
  max_instances = 10
  
  # Connect the connector to the default subnet of the VPC
  subnet {
    name = "default"
  }
}

# IAM: Grant Cloud Run services access to the VPC connector
resource "google_project_iam_member" "cloudrun_vpc_access" {
  project = var.project_id
  role    = "roles/vpcaccess.user"
  member  = "serviceAccount:${google_service_account.orchestrator_sa.email}"
}

# Firewall rule to allow internal communication (optional, but recommended)
resource "google_compute_firewall" "allow_internal" {
  depends_on = [google_project_service.apis["compute.googleapis.com"]]
  
  name    = "allow-internal-ai-ecosystem"
  network = var.network_name
  
  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "icmp"
  }
  
  source_ranges = [var.vpc_connector_cidr]
  target_tags   = ["ai-ecosystem"]
}
