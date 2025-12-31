# Camera Trap Species Detection Platform - Terraform Variables
#
# Copyright (c) 2025 Omar Miranda
# SPDX-License-Identifier: Apache-2.0

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "eu-central-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "species-detection"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "RDS maximum allocated storage in GB for autoscaling"
  type        = number
  default     = 100
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "species_detection"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "species_admin"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 900
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 3008
}

variable "alert_email" {
  description = "Email for CloudWatch alerts"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name for image storage"
  type        = string
}
