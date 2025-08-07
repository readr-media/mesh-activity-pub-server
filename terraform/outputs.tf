output "cloud_run_url" {
  description = "Cloud Run 服務 URL"
  value       = google_cloud_run_service.main.status[0].url
}

output "database_connection_name" {
  description = "Cloud SQL 連接名稱"
  value       = google_sql_database_instance.main.connection_name
}

output "database_ip_address" {
  description = "Cloud SQL IP 地址"
  value       = google_sql_database_instance.main.ip_address.0.ip_address
}

output "redis_host" {
  description = "Redis 主機地址"
  value       = google_redis_instance.cache.host
}

output "redis_port" {
  description = "Redis 端口"
  value       = google_redis_instance.cache.port
}

output "container_registry_url" {
  description = "Container Registry URL"
  value       = "gcr.io/${var.project_id}"
}
