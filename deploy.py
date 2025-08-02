#!/usr/bin/env python3

import argparse
import boto3
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Deploy AI Agent to AWS')
    parser.add_argument('--stack-name', default='ai-agent-stack',
                        help='CloudFormation stack name')
    parser.add_argument('--region', default='us-east-1',
                        help='AWS region to deploy to')
    parser.add_argument('--model-id', 
                        default='anthropic.claude-3-sonnet-20240229-v1:0',
                        help='AWS Bedrock model ID')
    parser.add_argument('--max-rpm', type=int, default=50,
                        help='Maximum requests per minute to AWS Bedrock')
    parser.add_argument('--profile', help='AWS CLI profile to use')
    return parser.parse_args()

def create_deployment_package():
    """Create a deployment package for Lambda function."""
    print("Creating Lambda deployment package...")
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a zip file
        zip_path = os.path.join(temp_dir, 'lambda_package.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add Lambda handler and helper modules
            lambda_dir = Path('agents/aws_lambda')
            for py_file in lambda_dir.glob('*.py'):
                zipf.write(py_file, arcname=py_file.name)
            
            # Add any additional dependencies
            # Note: boto3 is already available in the Lambda environment
        
        return zip_path
    except Exception as e:
        print(f"Error creating deployment package: {e}")
        shutil.rmtree(temp_dir)
        raise

def upload_to_s3(s3_client, zip_path, bucket_name, key):
    """Upload deployment package to S3."""
    print(f"Uploading deployment package to S3 bucket: {bucket_name}")
    try:
        s3_client.upload_file(zip_path, bucket_name, key)
        return f"s3://{bucket_name}/{key}"
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        raise

def create_or_update_stack(cf_client, stack_name, template_path, parameters):
    """Create or update CloudFormation stack."""
    # Read CloudFormation template
    with open(template_path, 'r') as f:
        template_body = f.read()
    
    # Check if stack exists
    stack_exists = False
    try:
        cf_client.describe_stacks(StackName=stack_name)
        stack_exists = True
    except cf_client.exceptions.ClientError:
        pass
    
    # Create or update stack
    try:
        if stack_exists:
            print(f"Updating stack: {stack_name}")
            cf_client.update_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Parameters=parameters,
                Capabilities=['CAPABILITY_IAM']
            )
        else:
            print(f"Creating stack: {stack_name}")
            cf_client.create_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Parameters=parameters,
                Capabilities=['CAPABILITY_IAM']
            )
        
        print("Waiting for stack operation to complete...")
        waiter = cf_client.get_waiter('stack_create_complete' if not stack_exists else 'stack_update_complete')
        waiter.wait(StackName=stack_name)
        
        # Get stack outputs
        response = cf_client.describe_stacks(StackName=stack_name)
        outputs = response['Stacks'][0]['Outputs']
        print("\nDeployment completed successfully!")
        print("\nStack Outputs:")
        for output in outputs:
            print(f"{output['OutputKey']}: {output['OutputValue']}")
        
    except Exception as e:
        print(f"Error deploying CloudFormation stack: {e}")
        raise

def main():
    """Main deployment function."""
    args = parse_args()
    
    # Initialize AWS clients
    session_kwargs = {}
    if args.profile:
        session_kwargs['profile_name'] = args.profile
    
    session = boto3.Session(region_name=args.region, **session_kwargs)
    s3_client = session.client('s3')
    cf_client = session.client('cloudformation')
    
    try:
        # Create deployment package
        zip_path = create_deployment_package()
        
        # Create a temporary S3 bucket for deployment
        deployment_bucket = f"ai-agent-deployment-{session.region_name}-{session.client('sts').get_caller_identity()['Account']}"
        try:
            s3_client.head_bucket(Bucket=deployment_bucket)
        except s3_client.exceptions.ClientError:
            print(f"Creating deployment bucket: {deployment_bucket}")
            s3_client.create_bucket(
                Bucket=deployment_bucket,
                CreateBucketConfiguration={
                    'LocationConstraint': session.region_name
                } if session.region_name != 'us-east-1' else {}
            )
        
        # Upload deployment package to S3
        s3_key = 'lambda/ai-agent-lambda.zip'
        s3_location = upload_to_s3(s3_client, zip_path, deployment_bucket, s3_key)
        
        # Update CloudFormation template parameters
        parameters = [
            {
                'ParameterKey': 'BedrockModelId',
                'ParameterValue': args.model_id
            },
            {
                'ParameterKey': 'MaxRequestsPerMinute',
                'ParameterValue': str(args.max_rpm)
            }
        ]
        
        # Deploy CloudFormation stack
        create_or_update_stack(cf_client, args.stack_name, 'template.yaml', parameters)
        
    except Exception as e:
        print(f"Deployment failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())