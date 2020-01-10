variable "aws_profile" {
  default = null
}

variable "aws_region" {
  default = null
}

variable "aws_access_key" {
  default = null
}

variable "aws_secret_key" {
  default = null
}

variable "public_key_path" {
  description = "The path to the public key that will be used to SSH the instances in this region."
  default     = ""
}

variable "public_key" {
  description = "The public key that will be used to SSH the instances in this region. Will override public_key_path if set."
  default     = ""
}

variable "subdomain_names" {
  description = "The [value] in the final '[value].[root_domain]' DNS name for each chain."
  default     = {}
}

variable "root_domain" {
  description = "The [root_domain] in the final '[value].[root_domain]' DNS name, should end in a TLD (e.g. eximchain.com)."
  default     = ""
}

variable "prefix" {
}

variable "key_name" {
}

variable "vpc_cidr" {
}

variable "public_subnet_cidr" {
}

variable "db_subnet_cidr" {
}

variable "dns_zone_name" {
}

variable "instance_type" {
}

variable "root_block_size" {
}

variable "pool_size" {
  default = {}
}

variable "use_placement_group" {
  default = {}
}

variable "key_content" {
  default = ""
}

variable "chains" {
  default = []
}

variable "chain_db_id" {
  default = {}
}

variable "chain_db_name" {
  default = {}
}

variable "chain_db_username" {
  default = {}
}

variable "chain_db_password" {
  default = {}
}

variable "chain_db_storage" {
  default = {}
}

variable "chain_db_storage_type" {
  default = {}
}

variable "chain_db_iops" {
  default = {}
}

variable "chain_db_instance_class" {
  default = {}
}

variable "chain_db_version" {
  default = {}
}

variable "chain_elixir_version" {
  default = {}
}

variable "secret_key_base" {
  default = {}
}

variable "alb_ssl_policy" {
  default = {}
}

variable "alb_certificate_arn" {
  default = {}
}

variable "use_ssl" {
  default = {}
}

variable "chain_jsonrpc_url" {
  default = {}
}
