data "aws_ami" "explorer" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_launch_configuration" "explorer" {
  name_prefix                 = "${var.prefix}-explorer-launchconfig"
  image_id                    = data.aws_ami.explorer.id
  instance_type               = var.instance_type
  security_groups             = [aws_security_group.app.id]
  key_name                    = aws_key_pair.blockscout.key_name
  iam_instance_profile        = aws_iam_instance_profile.explorer.id
  associate_public_ip_address = false

  depends_on = [aws_db_instance.default]

  user_data = file("${path.module}/libexec/init.sh")

  root_block_device {
    volume_size = var.root_block_size
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_placement_group" "explorer" {
  count    = length(matchkeys(keys(var.use_placement_group),values(var.use_placement_group),["True"])) 
  name     = "${var.prefix}-${var.chains[count.index]}-explorer-pg"
  strategy = "cluster"
}

resource "aws_autoscaling_group" "explorer_a" {
  count                = length(var.chains)
  name                 = "${var.prefix}-${var.chains[count.index]}-asg-a"
  max_size             = "4"
  min_size             = "1"
  desired_capacity     = "1"
  launch_configuration = aws_launch_configuration.explorer.name
  vpc_zone_identifier  = [aws_subnet.default.id]
  target_group_arns    = [aws_lb_target_group.explorer[0].arn]
  placement_group      = var.use_placement_group[var.chains[count.index]] == "True" ? "${var.prefix}-${var.chains[count.index]}-explorer-pg" : null

  # Health checks are performed by CodeDeploy hooks
  health_check_type = "EC2"

  enabled_metrics = [
    "GroupMinSize",
    "GroupMaxSize",
    "GroupDesiredCapacity",
    "GroupInServiceInstances",
    "GroupTotalInstances",
  ]

  depends_on = [
    aws_ssm_parameter.db_host,
    aws_ssm_parameter.db_name,
    aws_ssm_parameter.db_port,
    aws_ssm_parameter.db_username,
    aws_ssm_parameter.db_password,
    aws_ssm_parameter.elixir_version,
    aws_ssm_parameter.secret_key_base,
    aws_ssm_parameter.jsonrpc_url,
    aws_placement_group.explorer
  ]

  lifecycle {
    create_before_destroy = true
  }

  tag {
    key                 = "prefix"
    value               = var.prefix
    propagate_at_launch = true
  }

  tag {
    key                 = "chain"
    value               = var.chains[count.index]
    propagate_at_launch = true
  }

  tag {
    key                 = "Name"
    value               = "${var.chains[count.index]} Application"
    propagate_at_launch = true
  }
}

resource "aws_autoscaling_group" "explorer_b" {
  count                = length(var.chains)
  name                 = "${var.prefix}-${var.chains[count.index]}-asg-b"
  max_size             = "4"
  min_size             = "1"
  desired_capacity     = "1"
  launch_configuration = aws_launch_configuration.explorer.name
  vpc_zone_identifier  = [aws_subnet.default.id]
  target_group_arns    = [aws_lb_target_group.explorer[0].arn]
  placement_group      = var.use_placement_group[var.chains[count.index]] == "True" ? "${var.prefix}-${var.chains[count.index]}-explorer-pg" : null

  # Health checks are performed by CodeDeploy hooks
  health_check_type = "EC2"

  enabled_metrics = [
    "GroupMinSize",
    "GroupMaxSize",
    "GroupDesiredCapacity",
    "GroupInServiceInstances",
    "GroupTotalInstances",
  ]

  depends_on = [
    aws_ssm_parameter.db_host,
    aws_ssm_parameter.db_name,
    aws_ssm_parameter.db_port,
    aws_ssm_parameter.db_username,
    aws_ssm_parameter.db_password,
    aws_ssm_parameter.elixir_version,
    aws_ssm_parameter.secret_key_base,
    aws_ssm_parameter.jsonrpc_url,
    aws_placement_group.explorer
  ]

  lifecycle {
    create_before_destroy = true
  }

  tag {
    key                 = "prefix"
    value               = var.prefix
    propagate_at_launch = true
  }

  tag {
    key                 = "chain"
    value               = var.chains[count.index]
    propagate_at_launch = true
  }

  tag {
    key                 = "Name"
    value               = "${var.chains[count.index]} Application"
    propagate_at_launch = true
  }
}

