# ---------------------------------------------------------------------------------------------------------------------
# EXTERNAL DNS RECORD
# ---------------------------------------------------------------------------------------------------------------------
locals {
  using_custom_domains = var.subdomain_names != {} && var.root_domain != ""
  custom_domains       = zipmap(keys(var.subdomain_names), formatlist("%s.${var.root_domain}", values(var.subdomain_names)))
}

data "aws_route53_zone" "domain" {
  count = local.using_custom_domains ? 1 : 0
  name  = "${var.root_domain}."
}

resource "aws_route53_record" "tx_executor" {
  count = local.using_custom_domains ? length(var.chains) : 0

  zone_id                  = element(data.aws_route53_zone.domain.*.zone_id, 0)
  name                     = local.custom_domains[element(var.chains, count.index)]
  type                     = "CNAME"
  ttl                      = "300"
  records                  = [element(aws_lb.explorer.*.dns_name, count.index)]
}

# Internal DNS Zone
resource "aws_route53_zone" "main" {
  name   = "${var.prefix}.${var.dns_zone_name}"
  vpc {
    vpc_id = aws_vpc.vpc.id
  }

  tags = {
    prefix = var.prefix
    origin = "terraform"
  }
}

# Private DNS records
resource "aws_route53_record" "db" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "db${count.index}"
  type    = "A"
  count   = length(var.chains)

  alias {
    name                   = aws_db_instance.default[count.index].address
    zone_id                = aws_db_instance.default[count.index].hosted_zone_id
    evaluate_target_health = false
  }
}

