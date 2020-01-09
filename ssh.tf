resource "aws_key_pair" "blockscout" {
  key_name_prefix = "exim-blockscout-explorer-"
  public_key      = var.public_key == "" ? file(var.public_key_path) : var.public_key
}

