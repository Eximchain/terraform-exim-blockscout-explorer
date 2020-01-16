import argparse
import boto3
import os.path
import zipfile
import tempfile
import contextlib
import time

POLL_SLEEP_SECONDS = 30

ONE_MB = 1 << 20
PART_SIZE = 6 * ONE_MB

# Most, but not all, python installations will have zlib. This is required to
# compress any files we send via a push. If we can't compress, we can still
# package the files in a zip container.
try:
    import zlib
    ZIP_COMPRESSION_MODE = zipfile.ZIP_DEFLATED
except ImportError:
    ZIP_COMPRESSION_MODE = zipfile.ZIP_STORED

codedeploy = boto3.client('codedeploy')
s3 = boto3.resource('s3')
autoscaling = boto3.client('autoscaling')

# Main Flow

def parse_args():
    parser = argparse.ArgumentParser(description='Deploy a blockscout revision to the specified application')
    parser.add_argument('--application-name', dest='application_name', required=True)
    parser.add_argument('--blockscout-source', dest='blockscout_source', required=True)
    parser.add_argument('--blockscout-ignore-hidden-files', dest='blockscout_ignore_hidden_files', action='store_true', default=False)
    parser.add_argument('--blockscout-revision-key', dest='blockscout_revision_key', required=True)
    return parser.parse_args()

def run(args):
    application_name = args.application_name
    deployment_group_name = application_name + '-dg0'
    revision_bucket = application_name + '-codedeploy-releases'
    blockscout_source_dir = args.blockscout_source
    blockscout_ignore_hidden_files = args.blockscout_ignore_hidden_files
    blockscout_revision_key = args.blockscout_revision_key

    deployment_group_response = codedeploy.get_deployment_group(applicationName=application_name, deploymentGroupName=deployment_group_name)
    current_asg, other_asg = get_asgs_from_deployment_group(deployment_group_response)
    asg_flag = current_asg[-1]

    if asg_flag == 'a':
        a_fleet = current_asg
        b_fleet = other_asg
        prepare_b_fleet(b_fleet)
        release_upload = push_release(application_name, blockscout_source_dir, blockscout_ignore_hidden_files, revision_bucket, blockscout_revision_key)
        wait_for_b_fleet_launch(b_fleet)
        print("Deploying to fleet B")
        deployment_id_b = deploy_to_target(b_fleet, application_name, deployment_group_name, release_upload)
        wait_for_deploy(deployment_id_b)
        print("Deploying back to fleet A")
        deployment_id_a = deploy_to_target(a_fleet, application_name, deployment_group_name, release_upload)
        wait_for_deploy(deployment_id_a)
        spin_down_b_fleet(b_fleet)
        wait_for_b_fleet_spin_down(b_fleet)
    elif asg_flag == 'b':
        print("Fleet B is active. Deploying back to fleet A")
        a_fleet = other_asg
        b_fleet = current_asg
        location = get_current_revision_location(application_name, deployment_group_name)
        release_upload = s3.Object(location['bucket'], location['key'])
        deployment_id_a = deploy_to_target(a_fleet, application_name, deployment_group_name, release_upload)
        wait_for_deploy(deployment_id_a)
        spin_down_b_fleet(b_fleet)
        wait_for_b_fleet_spin_down(b_fleet)
    else:
        raise RuntimeError(f'Current ASG {current_asg} must end in "a" or "b"')

# Individual Steps

def push_release(app_name, blockscout_source_dir, blockscout_ignore_hidden_files, revision_bucket, revision_key):
    with make_bundle(blockscout_source_dir, blockscout_ignore_hidden_files) as bundle:
        try:
            upload = s3_upload(bundle, revision_bucket, revision_key)
            register_blockscout_revision(app_name, revision_bucket, revision_key, upload.e_tag, upload.version_id)
            print("Blockscout Release successfully pushed")
            return upload
        except Exception as e:
            raise RuntimeError("Error pushing release: ", e)

def prepare_b_fleet(asg_name):
    print("Preparing fleet B")
    autoscaling.set_desired_capacity(AutoScalingGroupName=asg_name, DesiredCapacity=1)

def wait_for_b_fleet_launch(asg_name):
    print("Waiting for fleet B")
    while True:
        response = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
        instances = response['AutoScalingGroups'][0]['Instances']
        num_instances = len(instances)

        if num_instances == 0:
            print(f'ASG {asg_name} still launching instance, sleeping {POLL_SLEEP_SECONDS} before retrying.')
            time.sleep(POLL_SLEEP_SECONDS)
        else:
            print(f'ASG {asg_name} successfully launched {num_instances} instance')
            return

def spin_down_b_fleet(asg_name):
    print("Spinning Down fleet B")
    autoscaling.set_desired_capacity(AutoScalingGroupName=asg_name, DesiredCapacity=0)

def wait_for_b_fleet_spin_down(asg_name):
    print("Waiting for fleet B")
    while True:
        response = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
        instances = response['AutoScalingGroups'][0]['Instances']
        num_instances = len(instances)

        if num_instances != 0:
            print(f'ASG {asg_name} still destroying instance, sleeping {POLL_SLEEP_SECONDS} before retrying.')
            time.sleep(POLL_SLEEP_SECONDS)
        else:
            print(f'ASG {asg_name} successfully destroyed {num_instances} instance')
            return

def deploy_to_target(target_asg, application_name, deployment_group_name, release):
    revision = {
        'revisionType': 'S3',
        's3Location': {
            'bucket': release.bucket_name,
            'key': release.key,
            'bundleType': 'zip',
            'version': release.version_id,
            'eTag': release.e_tag
        }
    }
    targets = {
        'autoScalingGroups': [target_asg]
    }

    deploy_response = codedeploy.create_deployment(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        revision=revision,
        deploymentConfigName='CodeDeployDefault.OneAtATime',
        targetInstances=targets
    )
    deployment_id = deploy_response['deploymentId']
    print(f'CodeDeploy deployment {deployment_id} successfully created')
    return deployment_id

@contextlib.contextmanager
def make_bundle(source, ignore_hidden_files=False):
    source_path = os.path.abspath(source)
    appspec_path = os.path.sep.join([source_path, 'appspec.yml'])
    with tempfile.TemporaryFile('w+b') as tf:
        zf = zipfile.ZipFile(tf, 'w', allowZip64=True)
        # Using 'try'/'finally' instead of 'with' statement since ZipFile
        # does not have support context manager in Python 2.6.
        try:
            contains_appspec = False
            for root, dirs, files in os.walk(source, topdown=True):
                if ignore_hidden_files:
                    files = [fn for fn in files if not fn.startswith('.')]
                    dirs[:] = [dn for dn in dirs if not dn.startswith('.')]
                for fn in files:
                    filename = os.path.join(root, fn)
                    filename = os.path.abspath(filename)
                    arcname = filename[len(source_path) + 1:]
                    if filename == appspec_path:
                        contains_appspec = True
                    zf.write(filename, arcname, ZIP_COMPRESSION_MODE)
            if not contains_appspec:
                raise RuntimeError(
                    '{0} was not found'.format(appspec_path)
                )
        finally:
            zf.close()
        yield tf

def s3_upload(bundle, dest_bucket, dest_key):
    object = s3.Object(dest_bucket, dest_key)
    print(f'Uploading bundle to Amazon S3 bucket {dest_bucket} key {dest_key}')

    filesize = bundle_size(bundle)
    mp = object.initiate_multipart_upload()
    part_num = 0
    parts = []
    with bundle as fp:
        try:
            while (fp.tell() < filesize):
                part_num += 1
                data = fp.read(PART_SIZE)
                print(f'uploading part {part_num} (Bytes Uploaded: {fp.tell()} / {filesize})')
                part = mp.Part(part_num).upload(Body=data)
                parts.append({"PartNumber": part_num, "ETag": part["ETag"]})
        except Exception as e:
            print(f'multipart upload FAILED')
            print(e)
            return mp.abort()
        else:
            return mp.complete(MultipartUpload={'Parts': parts})

def register_blockscout_revision(app_name, bucket, key, etag, version):
    revision = {
        'revisionType': 'S3',
        's3Location': {
            'bucket': bucket,
            'key': key,
            'bundleType': 'zip',
            'eTag': etag,
            'version': version
        }
    }
    codedeploy.register_application_revision(applicationName=app_name, revision=revision)

def wait_for_deploy(deployment_id):
    while True:
        response = codedeploy.get_deployment(deploymentId=deployment_id)
        status = response['deploymentInfo']['status']

        if status == 'Succeeded':
            print(f'Deployment {deployment_id} Succeeded')
            return
        elif status == 'Failed':
            print(f'Deployment {deployment_id} Failed')
            raise RuntimeError(response['deploymentInfo']['errorInformation'])
        else:
            print(f'Deployment {deployment_id} still in progress with status {status}, sleeping {POLL_SLEEP_SECONDS} before retrying.')
            time.sleep(POLL_SLEEP_SECONDS)

def get_current_revision_location(app_name, deployment_group_name):
    response = codedeploy.get_deployment_group(applicationName=app_name, deploymentGroupName=deployment_group_name)
    revision_location = response['deploymentGroupInfo']['targetRevision']['s3Location']
    return revision_location

# Helper Functions

def bundle_size(bundle):
    bundle.seek(0, 2)
    size = bundle.tell()
    bundle.seek(0)
    return size

def get_asgs_from_deployment_group(get_deployment_group_response):
    current_asg = get_deployment_group_response['deploymentGroupInfo']['autoScalingGroups'][0]['name']
    asg_flag = current_asg[-1]
    asg_other_flag = 'a' if asg_flag == 'b' else 'b'
    other_asg = current_asg[:-1] + asg_other_flag

    print(f'Current: {current_asg}, Other: {other_asg}')
    return current_asg, other_asg

# Code Entry Point

# Executes the command specified in the provided argparse namespace
def execute_command(args):
    run(args)
    print("Full Deployment Successful")

args = parse_args()
execute_command(args)