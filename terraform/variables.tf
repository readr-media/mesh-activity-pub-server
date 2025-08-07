variable "project_id" {
  description = "GCP 專案 ID"
  type        = string
}

variable "region" {
  description = "GCP 地區"
  type        = string
  default     = "asia-east1"
}

variable "db_password" {
  description = "資料庫密碼"
  type        = string
  sensitive   = true
}

variable "graphql_endpoint" {
  description = "GraphQL 端點 URL"
  type        = string
  default     = "http://localhost:4000/graphql"
}

variable "activitypub_domain" {
  description = "ActivityPub 域名"
  type        = string
  default     = "activity.readr.tw"
}

variable "secret_key" {
  description = "應用程式密鑰"
  type        = string
  sensitive   = true
}

variable "github_owner" {
  description = "GitHub 擁有者"
  type        = string
  default     = "readr-media"
}

variable "github_repo" {
  description = "GitHub 儲存庫名稱"
  type        = string
  default     = "mesh-activity-pub-server"
}
