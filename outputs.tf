output "instructions" {
  description = "Instructions for executing deployments"

  value = <<OUTPUT
To deploy a new version of the application manually:

    1) Run the following command to upload the application to S3.

        aws deploy push --application-name=${aws_codedeploy_app.explorer.name} --s3-location s3://${aws_s3_bucket.explorer_releases.id}/path/to/release.zip --source=path/to/repo

    2) Follow the instructions in the output from the `aws deploy push` command
       to deploy the uploaded application. Use the deployment group names shown below:

        - ${join(
"\n        - ",
formatlist(
"%s",
aws_codedeploy_deployment_group.explorer.*.deployment_group_name,
),
)}

       You will also need to specify a deployment config name. Example:

        --deployment-config-name=CodeDeployDefault.OneAtATime

       A deployment description is optional.

    3) Monitor the deployment using the deployment id returned by the `aws deploy create-deployment` command:

        aws deploy get-deployment --deployment-id=<deployment-id>

    4) Once the deployment is complete, you can access each chain explorer from its respective url:

        - ${join(
"\n        - ",
formatlist(
"%s: %s",
keys(zipmap(var.chains, aws_lb.explorer.*.dns_name)),
values(zipmap(var.chains, aws_lb.explorer.*.dns_name)),
),
)}
OUTPUT

    }

