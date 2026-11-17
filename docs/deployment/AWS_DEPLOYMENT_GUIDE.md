# AWS Production Deployment & Security Guide

## 1. Target AWS Architecture (`ap-south-1` Mumbai Region)
- **Compute**: AWS ECS Fargate (or EKS) running separate `frontend` (Next.js) and `backend` (FastAPI/Gunicorn) services behind an Application Load Balancer (ALB) with AWS WAF.
- **Database**: Amazon RDS for PostgreSQL 16 (Multi-AZ, encrypted at rest with AWS KMS, automated daily snapshots with 14-day retention).
- **Cache & Distributed Locks**: Amazon ElastiCache for Redis 7 (coordinates 15-minute booking holds).
- **Object Storage**: Amazon S3 (`dreamsadverstings-media-ap-south-1`) with private ACLs and short-lived presigned PUT/GET URLs for vendor KYC documents and proof-of-display photographs.
- **Observability**: Amazon CloudWatch Logs, Container Insights, and metric alarms on 5xx rate, RDS CPU/connections, and payment webhook failures.
