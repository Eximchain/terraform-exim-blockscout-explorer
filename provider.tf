provider "aws" {
  version = "~> 2.17"
  region  = var.aws_region

  profile    = var.aws_profile
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}

