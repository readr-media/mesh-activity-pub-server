# 設定 Terraform 版本和提供者
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

# 設定 Google Cloud 提供者
provider "google" {
  project = var.project_id
  region  = var.region
}

# 啟用必要 API
resource "google_project_service" "required_apis" {
  for_each = toset([
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "containerregistry.googleapis.com",
    "sql-component.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com"
  ])
  
  service = each.value
  disable_dependent_services = true
}

# 建立 Cloud SQL 實例（PostgreSQL）
resource "google_sql_database_instance" "main" {
  name             = "mesh-activity-pub-db"
  database_version = "POSTGRES_14"
  region           = var.region
  
  settings {
    tier = "db-f1-micro"
    
    backup_configuration {
      enabled    = true
      start_time = "02:00"
    }
    
    ip_configuration {
      ipv4_enabled    = true
      require_ssl     = true
      authorized_networks {
        name  = "all"
        value = "0.0.0.0/0"
      }
    }
  }
  
  deletion_protection = false
}

# 建立資料庫
resource "google_sql_database" "database" {
  name     = "readr_mesh"
  instance = google_sql_database_instance.main.name
}

# 建立資料庫使用者
resource "google_sql_user" "users" {
  name     = "mesh_user"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

# 建立 Redis 實例
resource "google_redis_instance" "cache" {
  name           = "mesh-activity-pub-cache"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region
  
  redis_version = "REDIS_6_X"
  display_name  = "Mesh ActivityPub Cache"
  
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

# 建立 Cloud Run 服務
resource "google_cloud_run_service" "main" {
  name     = "mesh-activity-pub-server"
  location = var.region
  
  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/mesh-activity-pub-server:latest"
        
        ports {
          container_port = 8080
        }
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql+asyncpg://${google_sql_user.users.name}:${var.db_password}@${google_sql_database_instance.main.ip_address.0.ip_address}/${google_sql_database.database.name}"
        }
        
        env {
          name  = "GRAPHQL_ENDPOINT"
          value = var.graphql_endpoint
        }
        
        env {
          name  = "ACTIVITYPUB_DOMAIN"
          value = var.activitypub_domain
        }
        
        env {
          name  = "SECRET_KEY"
          value = var.secret_key
        }
        
        env {
          name  = "REDIS_URL"
          value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
        }
        
        resources {
          limits = {
            cpu    = "1000m"
            memory = "1Gi"
          }
        }
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
}

# 允許未認證存取
resource "google_cloud_run_service_iam_member" "public" {
  location = google_cloud_run_service.main.location
  service  = google_cloud_run_service.main.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# 建立 Cloud Build 觸發器
resource "google_cloudbuild_trigger" "main" {
  name        = "mesh-activity-pub-trigger"
  description = "Trigger for Mesh ActivityPub Server"
  
  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = "main"
    }
  }
  
  filename = "cloudbuild.yaml"
  
  substitutions = {
    _DATABASE_URL        = "postgresql+asyncpg://${google_sql_user.users.name}:${var.db_password}@${google_sql_database_instance.main.ip_address.0.ip_address}/${google_sql_database.database.name}"
    _GRAPHQL_ENDPOINT    = var.graphql_endpoint
    _ACTIVITYPUB_DOMAIN  = var.activitypub_domain
    _SECRET_KEY          = var.secret_key
    _REDIS_URL           = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
  }
}

# 輸出
output "cloud_run_url" {
  value = google_cloud_run_service.main.status[0].url
}

output "database_connection_name" {
  value = google_sql_database_instance.main.connection_name
}

output "redis_host" {
  value = google_redis_instance.cache.host
}
