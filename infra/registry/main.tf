terraform {
  required_version = ">= 1.6, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
provider "aws" {
  region = var.region
}
variable "region" {
  type    = string
  default = "us-west-2"
}
variable "repository_name" {
  type    = string
  default = "release-harbor"
}
resource "aws_ecr_repository" "harbor" {
  name                 = var.repository_name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "AES256"
  }
  tags = { Project = "ReleaseHarbor", ManagedBy = "Terraform" }
}
resource "aws_ecr_lifecycle_policy" "harbor" {
  repository = aws_ecr_repository.harbor.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Expire untagged images after 14 days"
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = 14
      }
      action = { type = "expire" }
    }]
  })
}
output "repository_url" {
  value = aws_ecr_repository.harbor.repository_url
}
