terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "ap-south-1"
}

variable "environment" {
  default = "production"
}

resource "aws_s3_bucket" "media_assets" {
  bucket = "dreamsadverstings-media-${var.environment}-ap-south-1"
}

resource "aws_s3_bucket_versioning" "media_versioning" {
  bucket = aws_s3_bucket.media_assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media_sse" {
  bucket = aws_s3_bucket.media_assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "media_assets_block" {
  bucket                  = aws_s3_bucket.media_assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_ecr_repository" "backend_repo" {
  name                 = "dreamsadverstings-backend"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "frontend_repo" {
  name                 = "dreamsadverstings-frontend"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/dreamsadverstings-${var.environment}"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "marketplace_cluster" {
  name = "dreamsadverstings-${var.environment}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
